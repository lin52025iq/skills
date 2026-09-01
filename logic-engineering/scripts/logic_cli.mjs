#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  readJson,
  writeJson,
  rootOf,
  iterNodes,
  buildNodeIndex,
  buildSymbolTable,
  semanticHash,
  unwrapValue,
  valueRef,
  valueType,
  compatibleTypes,
  enumContains,
  validatePlacement,
} from './lib/model.mjs';

function fail(message, extra = {}) {
  console.error(JSON.stringify({ ok: false, error: message, ...extra }, null, 2));
  process.exit(1);
}

function option(args, ...names) {
  for (const name of names) {
    const i = args.indexOf(name);
    if (i >= 0) return args[i + 1] ?? null;
  }
  return null;
}

function refsIn(value, out = []) {
  if (Array.isArray(value)) {
    for (const item of value) refsIn(item, out);
  } else if (value && typeof value === 'object') {
    if (typeof value.ref === 'string') out.push(value.ref);
    for (const item of Object.values(value)) refsIn(item, out);
  }
  return out;
}

function validateTypedValue(value, symbols, errors, owner, location) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    errors.push({ code: 'INVALID_TYPED_VALUE', semantic_id: owner, path: location, message: 'typed value 必须是对象' });
    return null;
  }
  const kinds = ['ref', 'literal', 'enum', 'null', 'set'].filter((key) => key in value);
  if (kinds.length !== 1) {
    errors.push({ code: 'INVALID_TYPED_VALUE', semantic_id: owner, path: location, message: '必须且只能包含 ref/literal/enum/null/set 之一' });
    return null;
  }
  if (value.ref) {
    if (!symbols[value.ref]) errors.push({ code: 'UNKNOWN_SYMBOL', semantic_id: owner, path: location, message: `未知 symbol: ${value.ref}` });
    return symbols[value.ref]?.type ?? null;
  }
  if (value.enum) {
    const type = value.enum.type;
    if (!symbols[type] || symbols[type].kind !== 'enum') {
      errors.push({ code: 'INVALID_ENUM_TYPE', semantic_id: owner, path: location, message: `非法 enum 类型: ${type}` });
    } else if (!enumContains(symbols, type, value.enum.value)) {
      errors.push({ code: 'INVALID_ENUM_VALUE', semantic_id: owner, path: location, message: `${value.enum.value} 不属于 ${type}` });
    }
    return type ?? null;
  }
  if (Array.isArray(value.set)) {
    for (let i = 0; i < value.set.length; i += 1) validateTypedValue(value.set[i], symbols, errors, owner, `${location}.set[${i}]`);
    return 'set';
  }
  return valueType(value, symbols);
}

function validateExpression(expr, symbols, errors, owner, location = 'expression') {
  if (!expr || typeof expr !== 'object' || Array.isArray(expr)) {
    errors.push({ code: 'INVALID_TYPED_EXPRESSION', semantic_id: owner, path: location, message: '表达式必须是对象' });
    return;
  }
  const op = expr.op;
  if (op === 'all' || op === 'any') {
    if (!Array.isArray(expr.items) || expr.items.length === 0) {
      errors.push({ code: 'INVALID_TYPED_EXPRESSION', semantic_id: owner, path: location, message: `${op} 需要非空 items` });
      return;
    }
    expr.items.forEach((item, i) => validateExpression(item, symbols, errors, owner, `${location}.items[${i}]`));
    return;
  }
  if (op === 'not') {
    validateExpression(expr.item, symbols, errors, owner, `${location}.item`);
    return;
  }
  if (!['eq', 'ne', 'lt', 'le', 'gt', 'ge', 'in', 'not_in'].includes(op)) {
    errors.push({ code: 'INVALID_TYPED_EXPRESSION', semantic_id: owner, path: location, message: `不支持 op: ${op}` });
    return;
  }
  const leftType = validateTypedValue(expr.left, symbols, errors, owner, `${location}.left`);
  if (op === 'in' || op === 'not_in') {
    if (!Array.isArray(expr.right?.set)) {
      errors.push({ code: 'INVALID_TYPED_EXPRESSION', semantic_id: owner, path: `${location}.right`, message: 'in/not_in 右侧必须是 typed set' });
      return;
    }
    expr.right.set.forEach((item, i) => {
      const itemType = validateTypedValue(item, symbols, errors, owner, `${location}.right.set[${i}]`);
      if (!compatibleTypes(leftType, itemType)) errors.push({ code: 'TYPE_MISMATCH', semantic_id: owner, path: location, message: `集合成员类型 ${itemType} 与 ${leftType} 不兼容` });
    });
    return;
  }
  const rightType = validateTypedValue(expr.right, symbols, errors, owner, `${location}.right`);
  if (!compatibleTypes(leftType, rightType)) errors.push({ code: 'TYPE_MISMATCH', semantic_id: owner, path: location, message: `比较类型 ${leftType} 与 ${rightType} 不兼容` });
}

function validateClm(document) {
  const root = rootOf(document);
  const errors = [];
  const warnings = [];
  const ids = new Set();
  const symbols = buildSymbolTable(document);
  const index = buildNodeIndex(document);

  for (const [collection, node] of iterNodes(document)) {
    const placement = validatePlacement(node, collection);
    if (placement) errors.push({ code: 'NODE_COLLECTION_MISMATCH', semantic_id: node.id, message: placement });
    if (ids.has(node.id)) errors.push({ code: 'DUPLICATE_SEMANTIC_ID', semantic_id: node.id, message: '语义 ID 重复' });
    ids.add(node.id);

    for (const ref of refsIn(node)) {
      if (!symbols[ref] && !index.has(ref) && !ref.startsWith('error.') && !ref.startsWith('event.') && !ref.startsWith('evidence.')) {
        errors.push({ code: 'BROKEN_REFERENCE', semantic_id: node.id, message: `引用不存在: ${ref}` });
      }
    }

    for (const key of ['expression', 'when', 'guard', 'condition']) {
      if (node[key]?.op) validateExpression(node[key], symbols, errors, node.id, key);
    }

    if (node.kind === 'action' && node.operation === 'assign') {
      const leftType = validateTypedValue(node.target, symbols, errors, node.id, 'target');
      const rightType = validateTypedValue(node.value, symbols, errors, node.id, 'value');
      if (!compatibleTypes(leftType, rightType)) errors.push({ code: 'TYPE_MISMATCH', semantic_id: node.id, message: `赋值类型 ${leftType} 与 ${rightType} 不兼容` });
    }

    if (node.kind === 'scenario') {
      for (const section of ['given', 'then']) {
        for (let i = 0; i < (node[section] ?? []).length; i += 1) {
          const assignment = node[section][i];
          const leftType = validateTypedValue(assignment.target, symbols, errors, node.id, `${section}[${i}].target`);
          const rightType = validateTypedValue(assignment.value, symbols, errors, node.id, `${section}[${i}].value`);
          if (!compatibleTypes(leftType, rightType)) errors.push({ code: 'TYPE_MISMATCH', semantic_id: node.id, message: `Scenario ${section} 类型不兼容` });
        }
      }
      for (const ref of node.when ?? []) if (!index.has(ref)) errors.push({ code: 'BROKEN_REFERENCE', semantic_id: node.id, message: `Scenario when 引用不存在: ${ref}` });
    }

    if (node.origin === 'observed' && !(node.evidence_refs ?? []).length) errors.push({ code: 'MISSING_EVIDENCE', semantic_id: node.id, message: 'observed 节点必须绑定证据' });
  }

  const transitions = [...iterNodes(document)].map(([, node]) => node).filter((node) => node.kind === 'transition');
  const forbidden = new Set([...iterNodes(document)].map(([, node]) => node).filter((node) => node.kind === 'forbidden_transition').map((node) => `${node.from}->${node.to}`));
  for (const transition of transitions) {
    if (forbidden.has(`${transition.from}->${transition.to}`)) errors.push({ code: 'FORBIDDEN_TRANSITION_CONFLICT', semantic_id: transition.id, message: `${transition.from} → ${transition.to} 同时允许和禁止` });
  }

  return { valid: errors.length === 0, errors, warnings, stats: { nodes: ids.size, symbols: Object.keys(symbols).length, version: root.version } };
}

function renderValue(value) {
  const unwrapped = unwrapValue(value);
  if (unwrapped && typeof unwrapped === 'object' && unwrapped.ref) return unwrapped.ref;
  if (Array.isArray(unwrapped)) return unwrapped.map((item) => `“${item}”`).join('、');
  return String(unwrapped);
}

function renderExpression(expr) {
  if (!expr?.op) return String(expr ?? '');
  if (expr.op === 'all') return expr.items.map(renderExpression).join('，并且');
  if (expr.op === 'any') return expr.items.map(renderExpression).join('，或者');
  if (expr.op === 'not') return `不满足（${renderExpression(expr.item)}）`;
  const labels = { eq: '等于', ne: '不等于', lt: '小于', le: '小于等于', gt: '大于', ge: '大于等于', in: '属于', not_in: '不属于' };
  return `${renderValue(expr.left)}${labels[expr.op] ?? expr.op}${renderValue(expr.right)}`;
}

function renderHuman(document) {
  const root = rootOf(document);
  const index = buildNodeIndex(document);
  const chunks = [`# ${root.name ?? root.id} — 人类可读逻辑`, ''];
  for (const behavior of root.behaviors ?? []) {
    chunks.push(`## ${behavior.name ?? behavior.id}`, '', `标识：\`${behavior.id}\``);
    if ((behavior.preconditions ?? []).length) {
      chunks.push('', '### 前置条件');
      for (const ref of behavior.preconditions) {
        const rule = index.get(ref);
        chunks.push(`- ${rule?.expression ? renderExpression(rule.expression) : ref}。`);
      }
    }
    if ((behavior.flow ?? []).length) {
      chunks.push('', '### 处理过程');
      let order = 1;
      for (const ref of behavior.flow) {
        const node = index.get(ref);
        let text = ref;
        if (node?.kind === 'action' && node.operation === 'assign') text = `将 ${renderValue(node.target)} 设置为 ${renderValue(node.value)}`;
        chunks.push(`${order}. ${text}。`);
        order += 1;
      }
    }
    chunks.push('');
  }
  for (const scenario of root.scenarios ?? []) {
    chunks.push(`## 场景：${scenario.name ?? scenario.id}`, '');
    for (const assignment of scenario.given ?? []) chunks.push(`- 已知：${renderValue(assignment.target)} = ${renderValue(assignment.value)}`);
    chunks.push(`- 当：${(scenario.when ?? []).join('、')}`);
    for (const assignment of scenario.then ?? []) chunks.push(`- 则：${renderValue(assignment.target)} = ${renderValue(assignment.value)}`);
    chunks.push('');
  }
  return chunks.join('\n');
}

function testVectors(document) {
  const root = rootOf(document);
  const index = buildNodeIndex(document);
  const vectors = [];
  for (const node of index.values()) {
    if (node.kind === 'rule' && ['in', 'not_in'].includes(node.expression?.op)) {
      const subject = valueRef(node.expression.left);
      const values = unwrapValue(node.expression.right);
      if (subject && Array.isArray(values)) {
        for (const value of values) vectors.push({ id: `test.${node.id}.${value}`, source_semantic_id: node.id, kind: node.expression.op === 'in' ? 'rule_positive' : 'rule_negative', given: { [subject]: value }, when: null, expect: { rule_result: node.expression.op === 'in' } });
      }
    }
    if (node.kind === 'scenario') {
      const mapAssignments = (items) => Object.fromEntries((items ?? []).map((assignment) => [valueRef(assignment.target), unwrapValue(assignment.value)]).filter(([key]) => key));
      vectors.push({ id: `test.${node.id}.example`, source_semantic_id: node.id, kind: 'scenario', given: mapAssignments(node.given), when: { behaviors: node.when ?? [] }, expect: mapAssignments(node.then) });
    }
    if (node.kind === 'transition') vectors.push({ id: `test.${node.id}.allowed`, source_semantic_id: node.id, kind: 'state_transition', given: { state: node.from }, when: { trigger: node.trigger }, expect: { state: node.to } });
  }
  return { source_clm: root.id, test_vector_version: '0.2', vectors, warnings: vectors.length ? [] : ['当前模型没有生成测试向量'] };
}

function compileIir(document, profile) {
  const root = rootOf(document);
  const index = buildNodeIndex(document);
  const repositoryById = new Map();
  const portById = new Map();
  const unresolved = [];

  for (const effect of root.effects ?? []) {
    if (['write', 'persist', 'read'].includes(effect.kind)) {
      const aggregate = String(effect.resource ?? 'resource').replace(/^domain\./, '').split('.')[0];
      const id = `repository.${aggregate}`;
      if (!repositoryById.has(id)) repositoryById.set(id, { id, kind: 'repository_contract', name: `${aggregate} repository`, semantic_refs: [], operations: [] });
      const repo = repositoryById.get(id);
      repo.semantic_refs.push(effect.id);
      const operation = effect.kind === 'read' ? 'load' : 'save';
      if (!repo.operations.includes(operation)) repo.operations.push(operation);
    }
    if (['external_call', 'emit'].includes(effect.kind)) {
      const id = `port.${effect.system ?? effect.kind}`;
      if (!portById.has(id)) portById.set(id, { id, kind: 'external_port', name: effect.system ?? effect.kind, semantic_refs: [], operations: [] });
      const port = portById.get(id);
      port.semantic_refs.push(effect.id);
      const operation = effect.operation ?? (effect.kind === 'emit' ? 'publish' : 'execute');
      if (!port.operations.includes(operation)) port.operations.push(operation);
    }
  }

  const repositories = [...repositoryById.values()];
  const externalPorts = [...portById.values()];
  const useCases = [];
  for (const behavior of root.behaviors ?? []) {
    const guards = (behavior.preconditions ?? []).map((id) => ({ semantic_id: id, expression: index.get(id)?.expression ?? null }));
    const steps = (behavior.flow ?? []).map((id) => {
      const node = index.get(id);
      if (!node) {
        unresolved.push({ semantic_id: id, kind: 'missing_node', blocking: true });
        return { semantic_id: id, unresolved: true };
      }
      return { semantic_id: id, kind: node.kind, operation: node.operation, target: node.target, value: node.value, effects: node.effects ?? [], when: node.when, then: node.then, else: node.else };
    });
    const dependencies = [
      ...repositories.filter((repo) => repo.semantic_refs.some((ref) => steps.some((step) => (step.effects ?? []).includes(ref)))).map((repo) => repo.id),
      ...externalPorts.filter((port) => port.semantic_refs.some((ref) => steps.some((step) => (step.effects ?? []).includes(ref)))).map((port) => port.id),
    ];
    useCases.push({ id: `usecase.${behavior.id.replace('behavior.', '')}`, semantic_id: behavior.id, name: behavior.name, kind: 'use_case', guards, steps, dependencies, failures: behavior.failures ?? [], postconditions: behavior.postconditions ?? [] });
  }

  return {
    iir: {
      version: '0.2',
      source_clm_id: root.id,
      source_clm_version: root.version,
      source_semantic_hash: semanticHash(document),
      target_profile: profile,
      use_cases: useCases,
      repository_contracts: repositories,
      external_ports: externalPorts,
      transactions: [],
      concurrency_plans: [],
      retry_plans: [],
      idempotency_plans: [],
      error_mappings: (root.behaviors ?? []).flatMap((behavior) => (behavior.failures ?? []).map((error) => ({ semantic_error_ref: error }))),
      primitive_bindings: [],
      generation_regions: [{ id: 'generation.domain', mode: 'generated' }, { id: 'generation.adapters', mode: 'contract_or_handwritten' }],
      traceability: useCases.map((useCase) => ({ implementation_id: useCase.id, semantic_refs: [useCase.semantic_id] })),
      unresolved,
    },
  };
}

function validateIir(document) {
  const root = document.iir ?? document;
  const errors = [];
  if (String(root.version) !== '0.2') errors.push({ code: 'IIR_VERSION', message: 'IIR version 必须为 0.2' });
  const dependencies = new Set([...(root.repository_contracts ?? []), ...(root.external_ports ?? [])].map((item) => item.id));
  for (const useCase of root.use_cases ?? []) {
    for (const dep of useCase.dependencies ?? []) if (!dependencies.has(dep)) errors.push({ code: 'IIR_BROKEN_DEPENDENCY', message: `${useCase.id} 依赖不存在: ${dep}` });
  }
  for (const item of root.unresolved ?? []) if (typeof item === 'string' || item?.blocking !== false) errors.push({ code: 'IIR_BLOCKING_UNRESOLVED', message: typeof item === 'string' ? item : item.semantic_id ?? item.kind });
  return { valid: errors.length === 0, errors, warnings: [] };
}

function targetTests(vectors, iir) {
  const root = iir.iir ?? iir;
  const useCaseByBehavior = new Map((root.use_cases ?? []).map((useCase) => [useCase.semantic_id, useCase]));
  const cases = (vectors.vectors ?? []).map((vector) => {
    const behaviors = vector.when?.behaviors ?? [];
    const useCase = behaviors.length ? useCaseByBehavior.get(behaviors[0]) : null;
    return { id: vector.id, kind: vector.kind, source_semantic_id: vector.source_semantic_id, given: vector.given, when: vector.when, expect: vector.expect, use_case_id: useCase?.id ?? null, fake_dependencies: useCase?.dependencies ?? [] };
  });
  return { target_test_plan: { version: '0.1', target_profile: root.target_profile?.id ?? null, source_clm: root.source_clm_id, cases, summary: { total: cases.length } } };
}

function verifyManifest(directory) {
  const manifest = readJson(path.join(directory, 'manifest.json'));
  const errors = [];
  for (const artifact of manifest.artifacts ?? []) {
    const file = path.join(directory, artifact.path);
    if (!fs.existsSync(file)) {
      errors.push({ code: 'GENERATED_FILE_MISSING', path: artifact.path });
      continue;
    }
    const contentHash = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
    if (contentHash !== artifact.content_hash) errors.push({ code: 'GENERATED_FILE_DRIFT', path: artifact.path });
  }
  return { valid: errors.length === 0, errors };
}

function usage() {
  console.log(`logic_cli.mjs <command>\n\ncommands:\n  validate-clm\n  symbols\n  hash\n  render\n  test-vectors\n  compile-iir\n  validate-iir\n  target-tests\n  verify-manifest`);
}

const [command, ...args] = process.argv.slice(2);
try {
  if (command === 'validate-clm') {
    const result = validateClm(readJson(args[0]));
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.valid ? 0 : 1);
  }
  if (command === 'symbols') {
    const output = option(args, '-o', '--output');
    if (!output) fail('symbols 需要 -o/--output');
    writeJson(output, { symbols: buildSymbolTable(readJson(args[0])) });
  } else if (command === 'hash') {
    console.log(semanticHash(readJson(args[0])));
  } else if (command === 'render') {
    const text = renderHuman(readJson(args[0]));
    const output = option(args, '-o', '--output');
    if (output) {
      fs.mkdirSync(path.dirname(output), { recursive: true });
      fs.writeFileSync(output, text, 'utf8');
    } else console.log(text);
  } else if (command === 'test-vectors') {
    const result = testVectors(readJson(args[0]));
    const output = option(args, '-o', '--output');
    if (output) writeJson(output, result); else console.log(JSON.stringify(result, null, 2));
  } else if (command === 'compile-iir') {
    const profileDoc = readJson(args[1]);
    const result = compileIir(readJson(args[0]), profileDoc.target_profile ?? profileDoc);
    const output = option(args, '-o', '--output');
    if (output) writeJson(output, result); else console.log(JSON.stringify(result, null, 2));
  } else if (command === 'validate-iir') {
    const result = validateIir(readJson(args[0]));
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.valid ? 0 : 1);
  } else if (command === 'target-tests') {
    const result = targetTests(readJson(args[0]), readJson(args[1]));
    const output = option(args, '-o', '--output');
    if (output) writeJson(output, result); else console.log(JSON.stringify(result, null, 2));
  } else if (command === 'verify-manifest') {
    const result = verifyManifest(args[0]);
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.valid ? 0 : 1);
  } else {
    usage();
    process.exit(command ? 1 : 0);
  }
} catch (error) {
  fail(error.message, { stack: error.stack });
}
