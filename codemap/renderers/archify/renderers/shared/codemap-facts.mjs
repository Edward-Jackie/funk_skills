// Codemap 事实侧车：把 <name>.facts.json 内嵌进页面，并追加只读的 Passport 扩展。
// 无侧车时不做任何事，输出与原版一致。
import fs from 'node:fs';
import path from 'node:path';

const FACTS_SUFFIX = '.facts.json';

// 候选 <name>.candidate.json 或 <name>.json 对应的侧车路径
export function codemapFactsPath(inputPath) {
  const dir = path.dirname(inputPath);
  const base = path.basename(inputPath).replace(/\.candidate\.json$/, '').replace(/\.json$/, '');
  return path.join(dir, `${base}${FACTS_SUFFIX}`);
}

// 内嵌 JSON 时转义 < > & 与 {{，避免提前结束脚本块或命中模板占位符
function serializeFacts(value) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029')
    .replace(/\{\{/g, '{\\u007b');
}

const STYLE = `
    .cm-panel { margin-top: 0.52rem; padding: 0.5rem; max-height: 15rem; overflow: auto; border: 1px solid color-mix(in srgb, var(--cloud-stroke) 38%, var(--toolbar-border)); border-radius: 0.55rem; background: color-mix(in srgb, var(--cloud-fill) 14%, var(--panel)); font-size: 0.625rem; line-height: 1.5; color: var(--text-muted); }
    .cm-panel[hidden] { display: none; }
    html[data-preset="blueprint"] .cm-panel { border-radius: 0.18rem; }
    .cm-head { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.3rem; }
    .cm-eyebrow { color: var(--cloud-stroke); font-size: 0.5rem; font-weight: 800; letter-spacing: 0.08em; }
    .cm-detail { margin: 0 0 0.35rem; color: var(--text); white-space: pre-wrap; word-break: break-word; }
    .cm-chips { display: flex; flex-wrap: wrap; gap: 0.24rem; margin-bottom: 0.35rem; }
    .cm-chip { padding: 0.12rem 0.34rem; border: 1px solid color-mix(in srgb, var(--toolbar-border) 82%, transparent); border-radius: 999px; background: color-mix(in srgb, var(--panel) 68%, transparent); color: var(--text-faint); font-size: 0.5rem; letter-spacing: 0.04em; }
    .cm-chip[data-tone="ok"] { border-color: color-mix(in srgb, var(--backend-stroke) 55%, var(--toolbar-border)); color: var(--backend-stroke); }
    .cm-chip[data-tone="warn"] { border-color: color-mix(in srgb, var(--security-stroke, #f59e0b) 60%, var(--toolbar-border)); color: var(--security-stroke, #f59e0b); }
    .cm-chip[data-tone="bad"] { border-color: #ef4444; color: #ef4444; }
    .cm-chip[data-tone="mute"] { opacity: 0.7; }
    .cm-sec { margin-top: 0.35rem; }
    .cm-sec > b { display: block; color: var(--text-faint); font-size: 0.5rem; font-weight: 800; letter-spacing: 0.08em; }
    .cm-ref { display: block; margin-top: 0.12rem; word-break: break-all; }
    .cm-ref code { color: var(--text); font-size: inherit; }
    .cm-ref small { color: var(--cloud-stroke); font-size: inherit; }
    .cm-cond { margin: 0 0 0.35rem; color: var(--text); font-weight: 700; }
    .cm-go { appearance: none; padding: 0.2rem 0.55rem; border: 1px solid color-mix(in srgb, var(--cloud-stroke) 55%, var(--toolbar-border)); border-radius: 999px; background: transparent; color: var(--cloud-stroke); font: inherit; font-size: 0.55rem; font-weight: 700; cursor: pointer; }
    .cm-go:hover, .cm-go:focus-visible { background: color-mix(in srgb, var(--cloud-stroke) 16%, transparent); outline: 2px solid var(--cloud-stroke); outline-offset: 1px; }
    .cm-sub-badge { cursor: pointer; }
    .cm-sub-badge rect { fill: color-mix(in srgb, var(--cloud-stroke) 24%, var(--panel)); stroke: color-mix(in srgb, var(--cloud-stroke) 80%, transparent); stroke-width: 1; }
    .cm-sub-badge text { fill: var(--cloud-stroke); font-family: inherit; font-size: 8.5px; font-weight: 700; letter-spacing: 0; }
    .cm-sub-badge.is-business rect { fill: color-mix(in srgb, var(--security-stroke, #f59e0b) 16%, var(--panel)); stroke: var(--security-stroke, #f59e0b); }
    .cm-sub-badge.is-business text { fill: var(--security-stroke, #f59e0b); }
    .cm-sub-badge.is-conflict rect { fill: color-mix(in srgb, #ef4444 16%, var(--panel)); stroke: #ef4444; }
    .cm-sub-badge.is-conflict text { fill: #ef4444; }
    .cm-sub-badge.is-dense rect { stroke-width: 1.3; }
    .cm-sub-badge.is-dense text { font-weight: 800; }
    .cm-drill .cm-go { background: color-mix(in srgb, var(--cloud-stroke) 14%, transparent); font-size: 0.6rem; }
    .cm-drill.is-business .cm-go { border-color: var(--security-stroke, #f59e0b); color: var(--security-stroke, #f59e0b); background: color-mix(in srgb, var(--security-stroke, #f59e0b) 14%, transparent); }
    .cm-drill.is-conflict .cm-go { border-color: #ef4444; color: #ef4444; background: color-mix(in srgb, #ef4444 14%, transparent); }
    .cm-crumb { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; margin: 0 0 0.5rem; font-size: 0.6rem; color: var(--text-muted); }
    html[data-embed="true"] .cm-crumb { display: none; }
`;

const SCRIPT = `
(function () {
  'use strict';
  var dataEl = document.getElementById('codemap-facts-data');
  if (!dataEl) return;
  var facts;
  try { facts = JSON.parse(dataEl.textContent); } catch (_) { return; }
  var chip = document.getElementById('focus-chip');
  var summary = document.getElementById('focus-summary');
  var container = document.querySelector('.diagram-container');
  var svg = container && container.querySelector('svg');
  if (!chip || !summary || !svg) return;

  var graph = facts.graph || {};
  var titles = facts.titles || {};
  var graphs = facts.graphs || {};
  var SVG_NS = 'http://www.w3.org/2000/svg';
  var panel = document.createElement('div');
  panel.id = 'codemap-facts-panel';
  panel.className = 'cm-panel';
  panel.setAttribute('role', 'region');
  panel.setAttribute('aria-label', 'Codemap 业务事实');
  panel.hidden = true;
  summary.parentNode.insertBefore(panel, summary);

  var EVIDENCE_TONE = { 'runtime-verified': 'ok', 'source-verified': 'ok', 'human-confirmed': 'ok', 'inferred': 'warn', 'unverified': 'warn', 'conflict': 'bad' };
  var STATUS_TONE = { current: 'ok', 'needs-review': 'warn', stale: 'warn', conflict: 'bad' };

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }
  function chipEl(text, tone) {
    var c = el('span', 'cm-chip', text);
    if (tone) c.setAttribute('data-tone', tone);
    return c;
  }
  function subGraphId(sub) {
    if (!sub || typeof sub !== 'string') return null;
    return sub.split('/').pop().replace(/\\.ya?ml$/, '');
  }
  function navigate(graphId, nodeId) {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ source: 'codemap', type: 'open', graph: graphId, node: nodeId || null }, '*');
      return;
    }
    location.href = graphId + '.html' + (nodeId ? '#focus=' + encodeURIComponent(nodeId) : '');
  }
  function goButton(text, graphId, nodeId) {
    var b = el('button', 'cm-go', text);
    b.type = 'button';
    b.addEventListener('click', function () { navigate(graphId, nodeId); });
    return b;
  }
  function subMeta(sub) {
    var sid = subGraphId(sub);
    return graphs[sid] || { title: titles[sid] || sid };
  }
  function markSubgraphs() {
    if (!svg) return;
    Object.keys(facts.nodes || {}).forEach(function (id) {
      var fact = facts.nodes[id];
      if (!fact || !fact.sub) return;
      var g = svg.querySelector('[data-node-id="' + id + '"]');
      if (!g || g.querySelector('.cm-sub-badge')) return;
      var rect = g.querySelector('rect');
      if (!rect) return;
      var sid = subGraphId(fact.sub);
      var meta = subMeta(fact.sub);
      var count = meta.node_count || 0;
      var kindLabel = meta.status === 'conflict' ? '冲突下钻' : (meta.kind === 'business' ? '业务下钻' : '下钻');
      var label = '↳ ' + kindLabel + (count ? ' ' + count : '');
      var width = Math.max(46, 12 + label.length * 7.2);
      var rectX = +rect.getAttribute('x') || 0;
      var rectY = +rect.getAttribute('y') || 0;
      var rectW = +rect.getAttribute('width') || 0;
      var rectH = +rect.getAttribute('height') || 0;
      var height = 18;
      var x = rectX + rectW - width - 6;
      var y = rectY + rectH - height - 6;
      var fine = g.querySelector('[data-detail="fine"]');
      if (fine) {
        fine.setAttribute('text-anchor', 'start');
        fine.setAttribute('x', rectX + 10);
      }
      var dense = count >= 10 || (meta.edge_count || 0) >= 10;
      var badge = document.createElementNS(SVG_NS, 'g');
      badge.setAttribute('class', 'cm-sub-badge' + (meta.kind === 'business' ? ' is-business' : '') + (meta.status === 'conflict' ? ' is-conflict' : '') + (dense ? ' is-dense' : ''));
      badge.setAttribute('aria-hidden', 'true');
      var bg = document.createElementNS(SVG_NS, 'rect');
      bg.setAttribute('x', x);
      bg.setAttribute('y', y);
      bg.setAttribute('width', width);
      bg.setAttribute('height', height);
      bg.setAttribute('rx', 9);
      var text = document.createElementNS(SVG_NS, 'text');
      text.setAttribute('x', x + width / 2);
      text.setAttribute('y', y + 12.6);
      text.setAttribute('text-anchor', 'middle');
      text.textContent = label;
      var tip = document.createElementNS(SVG_NS, 'title');
      tip.textContent = '可下钻：' + (meta.title || sid) + (count ? '（' + count + ' 个节点' + (meta.edge_count ? ' · ' + meta.edge_count + ' 条关系' : '') + '）' : '');
      badge.appendChild(bg);
      badge.appendChild(text);
      badge.appendChild(tip);
      badge.addEventListener('click', function (event) {
        event.stopPropagation();
        navigate(sid, null);
      });
      g.appendChild(badge);
    });
  }
  function evidenceBlock(evidence) {
    if (!evidence || !evidence.level) return null;
    var sec = el('div', 'cm-sec');
    sec.appendChild(el('b', null, '证据'));
    var row = el('div', 'cm-chips');
    row.appendChild(chipEl(evidence.level, EVIDENCE_TONE[evidence.level] || null));
    sec.appendChild(row);
    if (evidence.note) sec.appendChild(el('div', null, evidence.note));
    return sec;
  }
  function refsBlock(refs) {
    if (!refs || !refs.length) return null;
    var sec = el('div', 'cm-sec');
    sec.appendChild(el('b', null, '源码锚点'));
    refs.forEach(function (ref) {
      var line = el('span', 'cm-ref');
      line.appendChild(el('code', null, ref.path));
      if (ref.symbol) {
        line.appendChild(document.createTextNode(' -> '));
        line.appendChild(el('small', null, ref.symbol));
      }
      sec.appendChild(line);
    });
    return sec;
  }
  function rulesBlock(rules) {
    if (!rules || !rules.length) return null;
    var sec = el('div', 'cm-sec');
    sec.appendChild(el('b', null, '规则'));
    var row = el('div', 'cm-chips');
    rules.forEach(function (rule) { row.appendChild(chipEl(String(rule), 'warn')); });
    sec.appendChild(row);
    return sec;
  }
  function graphLine() {
    var row = el('div', 'cm-chips');
    if (graph.status) row.appendChild(chipEl('图状态 ' + graph.status, STATUS_TONE[graph.status] || null));
    if (graph.verified_at) row.appendChild(chipEl('校验于 ' + graph.verified_at, 'mute'));
    if (graph.verified_commit) row.appendChild(chipEl(String(graph.verified_commit).slice(0, 7), 'mute'));
    return row;
  }
  function head(text) {
    var h = el('div', 'cm-head');
    h.appendChild(el('span', 'cm-eyebrow', text));
    return h;
  }

  function renderNode(id, fact) {
    panel.textContent = '';
    panel.appendChild(head('CODEMAP · 节点事实'));
    if (fact.detail) panel.appendChild(el('p', 'cm-detail', fact.detail));
    var metaChips = el('div', 'cm-chips');
    if (fact.kind) metaChips.appendChild(chipEl(fact.kind));
    if (fact.level != null) metaChips.appendChild(chipEl('L' + fact.level));
    panel.appendChild(metaChips);
    [evidenceBlock(fact.evidence), refsBlock(fact.refs), rulesBlock(fact.rules)].forEach(function (b) { if (b) panel.appendChild(b); });
    var subId = subGraphId(fact.sub);
    if (subId) {
      var meta = subMeta(fact.sub);
      var scope = meta.status === 'conflict' ? '冲突下钻' : (meta.kind === 'business' ? '业务下钻' : '下钻');
      var label = scope + ' → ' + (meta.title || titles[subId] || subId);
      if (meta.node_count) label += ' · ' + meta.node_count + ' 节点';
      var sec = el('div', 'cm-sec cm-drill' + (meta.kind === 'business' ? ' is-business' : '') + (meta.status === 'conflict' ? ' is-conflict' : ''));
      sec.appendChild(goButton(label, subId));
      var dense = [];
      if (meta.node_count) dense.push(meta.node_count + ' 个节点');
      if (meta.edge_count) dense.push(meta.edge_count + ' 条关系');
      if (dense.length) sec.appendChild(el('div', null, dense.join(' · ')));
      panel.appendChild(sec);
    }
    var tags = el('div', 'cm-chips');
    (fact.tags || []).forEach(function (t) { tags.appendChild(chipEl('#' + t)); });
    if (tags.childNodes.length) panel.appendChild(tags);
    panel.appendChild(graphLine());
    panel.hidden = false;
  }
  function renderEdge(id, fact) {
    panel.textContent = '';
    panel.appendChild(head('CODEMAP · 关系事实'));
    var cond = fact.condition;
    panel.appendChild(el('p', 'cm-cond', '条件：' + (!cond || cond === 'always' ? '无条件' : cond)));
    if (fact.detail) panel.appendChild(el('p', 'cm-detail', fact.detail));
    var chips = el('div', 'cm-chips');
    if (fact.kind) chips.appendChild(chipEl(fact.kind));
    panel.appendChild(chips);
    [evidenceBlock(fact.evidence), refsBlock(fact.refs), rulesBlock(fact.rules)].forEach(function (b) { if (b) panel.appendChild(b); });
    panel.appendChild(graphLine());
    panel.hidden = false;
  }

  function pinnedEdgeId() {
    var pin = svg.getAttribute('data-relationship-pin-active');
    if (!pin) return null;
    var edges = svg.querySelectorAll('[data-edge-key]');
    for (var i = 0; i < edges.length; i += 1) {
      if (edges[i].getAttribute('data-edge-key') === pin) return edges[i].getAttribute('data-edge-id');
    }
    return null;
  }
  var scheduled = false;
  function sync() {
    scheduled = false;
    if (chip.hidden) { panel.hidden = true; return; }
    var live = container && container.querySelector('svg');
    if (live && live !== svg) {
      svg = live;
      observeSvg();
      markSubgraphs();
    }
    if (!svg) { panel.hidden = true; return; }
    var edgeId = pinnedEdgeId();
    if (edgeId && facts.edges && facts.edges[edgeId]) { renderEdge(edgeId, facts.edges[edgeId]); return; }
    var focus = svg.getAttribute('data-focus-active');
    if (focus && focus.indexOf(' ') < 0 && facts.nodes && facts.nodes[focus]) { renderNode(focus, facts.nodes[focus]); return; }
    panel.hidden = true;
  }
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(sync);
    window.setTimeout(function () { if (scheduled) sync(); }, 120);
  }
  var svgObserver = new MutationObserver(schedule);
  function observeSvg() {
    svgObserver.disconnect();
    if (svg) svgObserver.observe(svg, { attributes: true, attributeFilter: ['data-relationship-pin-active', 'data-focus-active'] });
  }
  observeSvg();
  var chipObserver = new MutationObserver(schedule);
  chipObserver.observe(chip, { attributes: true, attributeFilter: ['hidden'] });
  var containerObserver = new MutationObserver(schedule);
  if (container) containerObserver.observe(container, { childList: true });
  document.addEventListener('click', schedule, true);
  document.addEventListener('focusin', schedule, true);
  schedule();
  markSubgraphs();

  // 上级图入口：放在图容器之前，嵌入模式隐藏（由外壳负责导航）
  if (graph.parent && graph.parent.graph) {
    var crumb = el('nav', 'cm-crumb');
    crumb.setAttribute('aria-label', 'Codemap 图层导航');
    crumb.appendChild(goButton('↑ 上级图：' + (titles[graph.parent.graph] || graph.parent.graph), graph.parent.graph, graph.parent.node));
    if (graph.title) crumb.appendChild(el('span', null, '当前：' + graph.title));
    container.parentNode.insertBefore(crumb, container);
  }

  // 外壳协议：收到 focus 消息时聚焦对应节点，让 Passport 展示
  window.addEventListener('message', function (event) {
    var data = event.data;
    if (!data || data.source !== 'codemap' || data.type !== 'focus' || typeof data.node !== 'string') return;
    if (svg.getAttribute('data-focus-active') === data.node) return;
    var nodes = svg.querySelectorAll('[data-node-id]');
    for (var i = 0; i < nodes.length; i += 1) {
      if (nodes[i].getAttribute('data-node-id') === data.node) {
        nodes[i].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        return;
      }
    }
  });
})();
`;

// 把事实块、样式和扩展脚本注入模板的 </body> 之前
export function injectCodemapFacts(template, factsText) {
  const facts = JSON.parse(factsText);
  if (facts?.schema !== 'codemap.facts/v1') {
    throw new Error(`Codemap facts sidecar has an unsupported schema: ${JSON.stringify(facts?.schema)}`);
  }
  const block = [
    `<script id="codemap-facts-data" type="application/json">${serializeFacts(facts)}</script>`,
    `<style id="codemap-facts-style">${STYLE}</style>`,
    `<script id="codemap-facts-extension">${SCRIPT}</script>`,
  ].join('\n');
  const index = template.lastIndexOf('</body>');
  if (index < 0) throw new Error('Codemap facts injection: template has no </body>');
  return `${template.slice(0, index)}${block}\n${template.slice(index)}`;
}

export function loadCodemapFacts(inputPath) {
  const factsPath = codemapFactsPath(inputPath);
  try {
    return fs.readFileSync(factsPath, 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}
