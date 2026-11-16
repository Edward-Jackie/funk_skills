// Codemap 画布只派发固定动作；业务写入由宿主的认证入口处理。
export const CODEMAP_INTERACTION_STYLE = `
  .diagram-container[data-codemap-canvas] { overscroll-behavior: contain; }
  .diagram-container[data-codemap-canvas] > svg { transition: none; }
  .cm-context-menu { position: fixed; z-index: 10000; min-width: 190px; max-width: calc(100vw - 16px); max-height: calc(100vh - 16px); overflow: auto; padding: 5px; border: 1px solid var(--toolbar-border); border-radius: 9px; background: var(--panel); color: var(--text); box-shadow: 0 12px 36px #0005; }
  .cm-context-menu[hidden] { display: none; }
  .cm-context-menu button { display: flex; gap: 9px; align-items: center; width: 100%; border: 0; border-radius: 5px; padding: 9px 12px; background: transparent; color: inherit; text-align: left; cursor: pointer; font: inherit; font-size: 12px; }
  .cm-context-menu button:hover, .cm-context-menu button:focus-visible { background: color-mix(in srgb, var(--cloud-stroke) 15%, var(--panel)); outline: 1px solid var(--cloud-stroke); }
  .cm-context-menu button[data-group-start] { margin-top: 4px; border-top: 1px solid var(--toolbar-border); border-radius: 0; }
  .cm-action-feedback { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); z-index: 10001; max-width: calc(100vw - 24px); padding: 7px 12px; border-radius: 6px; background: var(--panel); color: var(--text); font-size: 12px; }
  .cm-action-feedback:empty { display: none; }
`;

export const CODEMAP_INTERACTION_SCRIPT = `
(function () {
  'use strict';
  var data = document.getElementById('codemap-facts-data');
  var container = document.querySelector('.diagram-container');
  var svg = container && container.querySelector(':scope > svg');
  if (!data || !svg || !window.Archify || !Archify.view) return;
  var facts;
  try { facts = JSON.parse(data.textContent); } catch (_) { return; }
  var graph = facts.graph || {};
  function canonical(id) { return id && facts.id_map && facts.id_map.render_to_canonical ? facts.id_map.render_to_canonical[id] || id : id; }
  var parentOrigin = location.origin;
  try { if (document.referrer) parentOrigin = new URL(document.referrer).origin; } catch (_) {}
  var capabilities = [];
  var hostContext = {};
  var activeTarget = { kind: 'canvas' };
  var restoreFocus = null;
  var menu = document.createElement('div');
  menu.className = 'cm-context-menu';
  menu.setAttribute('role', 'menu');
  menu.setAttribute('aria-label', '地图操作');
  menu.hidden = true;
  document.body.appendChild(menu);
  var feedback = document.createElement('div');
  feedback.className = 'cm-action-feedback';
  feedback.setAttribute('role', 'status');
  document.body.appendChild(feedback);
  var feedbackTimer;
  function notify(text) {
    clearTimeout(feedbackTimer);
    feedback.textContent = text;
    feedbackTimer = setTimeout(function () { feedback.textContent = ''; }, 3500);
  }
  function post(message) {
    if (window.parent === window) return;
    window.parent.postMessage(Object.assign({ source: 'codemap' }, message), parentOrigin === 'null' ? '*' : parentOrigin);
  }
  function trusted(event) {
    return window.parent !== window && event.source === window.parent && event.origin === parentOrigin;
  }
  function targetFor(element) {
    var node = element.closest('[data-node-id]');
    if (node && facts.nodes[node.getAttribute('data-node-id')]) return { kind: 'node', node: node.getAttribute('data-node-id') };
    var edge = element.closest('[data-edge-id]');
    var hit = element.closest('[data-relationship-hit-key]');
    if (!edge && hit) {
      var key = hit.getAttribute('data-relationship-hit-key');
      edge = Array.prototype.find.call(svg.querySelectorAll('[data-edge-key]'), function (item) { return item.getAttribute('data-edge-key') === key; });
    }
    if (edge && facts.edges[edge.getAttribute('data-edge-id')]) return { kind: 'edge', edge: edge.getAttribute('data-edge-id') };
    return { kind: 'canvas' };
  }
  function selectedTarget() {
    var relation = Archify.focus.relationship();
    if (relation && relation.id && facts.edges[relation.id]) return { kind: 'edge', edge: relation.id };
    var selected = Archify.focus.active();
    if (typeof selected === 'string' && facts.nodes[selected]) return { kind: 'node', node: selected };
    return { kind: 'canvas' };
  }
  function detail(target) {
    if (target.node) Archify.focus.set(target.node, { toggle: false });
    else if (target.edge) Archify.focus.inspectRelationshipById(target.edge, { toggle: false });
  }
  function close(restore) {
    menu.hidden = true;
    if (restore && restoreFocus && document.contains(restoreFocus)) restoreFocus.focus();
  }
  // 主界面、键盘和右键菜单复用此动作表；新增动作必须明确能力与处理入口。
  var actions = [
    { id: 'details', label: '查看详情与条件', icon: 'i', group: 'object', visible: function (t) { return t.kind !== 'canvas'; }, run: detail },
    { id: 'focus', label: '聚焦对象', icon: '◎', group: 'object', visible: function (t) { return t.kind !== 'canvas'; }, run: function (t) {
      detail(t);
      if (t.node) Archify.view.reveal([t.node], { instant: true });
      else { var edge = Archify.focus.relationship(); if (edge) Archify.view.reveal([edge.from, edge.to], { instant: true }); }
    } },
    { id: 'open', label: '下钻子流程', icon: '↳', group: 'object', visible: function (t) { return t.node && facts.nodes[t.node].sub; }, run: function (t) {
      var id = String(facts.nodes[t.node].sub).split('/').pop().replace(/\\.ya?ml$/, '');
      if (!/^[a-z0-9-]+$/.test(id)) return;
      if (window.parent !== window) post({ type: 'open', graph: id });
      else location.href = id + '.html';
    } },
    { id: 'copy-link', label: '复制对象链接', icon: '↗', group: 'object', visible: function (t) { return t.kind !== 'canvas'; }, run: function (t) {
      var url = new URL(location.href);
      url.hash = t.node ? 'focus=' + encodeURIComponent(canonical(t.node)) : 'relation=' + encodeURIComponent(canonical(t.edge));
      if (!navigator.clipboard) { notify('当前浏览器不支持复制，请从地址栏复制链接'); return; }
      navigator.clipboard.writeText(url.href).then(function () { notify('对象链接已复制'); }, function () { notify('复制失败，请检查浏览器剪贴板权限'); });
    } },
    { id: 'zoom-in', label: '放大', icon: '+', group: 'view', run: function () { Archify.view.zoomIn(); } },
    { id: 'zoom-out', label: '缩小', icon: '−', group: 'view', run: function () { Archify.view.zoomOut(); } },
    { id: 'fit', label: '适应当前范围', icon: '⌖', group: 'view', run: function () {
      var selected = Archify.focus.active();
      if (selected) Archify.view.reveal(Array.isArray(selected) ? selected : [selected], { instant: true });
      else Archify.view.reset();
    } },
    { id: 'reset', label: '重置视图', icon: '↺', group: 'view', run: function () { Archify.view.reset(); } },
    { id: 'create-requirement', label: '发起需求变更', icon: '＋', group: 'work', visible: function () { return capabilities.indexOf('create-requirement') >= 0; }, run: function (t) {
      post({ type: 'action', action: 'create-requirement', graph: graph.id, node: canonical(t.node), edge: canonical(t.edge), context: hostContext });
    } }
  ];
  function run(id, target) {
    var action = actions.find(function (item) { return item.id === id; });
    if (!action || (action.visible && !action.visible(target))) return;
    close(false);
    action.run(target);
  }
  function show(target, x, y, source) {
    activeTarget = target;
    restoreFocus = source || document.activeElement;
    menu.textContent = '';
    var previousGroup = '';
    actions.filter(function (item) { return !item.visible || item.visible(target); }).forEach(function (action) {
      var button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('role', 'menuitem');
      button.setAttribute('data-action', action.id);
      if (previousGroup && previousGroup !== action.group) button.setAttribute('data-group-start', '');
      previousGroup = action.group;
      var icon = document.createElement('span');
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = action.icon;
      button.appendChild(icon);
      button.appendChild(document.createTextNode(action.label));
      button.addEventListener('click', function () { run(action.id, activeTarget); });
      menu.appendChild(button);
    });
    menu.hidden = false;
    menu.style.left = Math.max(8, Math.min(x, window.innerWidth - menu.offsetWidth - 8)) + 'px';
    menu.style.top = Math.max(8, Math.min(y, window.innerHeight - menu.offsetHeight - 8)) + 'px';
    menu.querySelector('button').focus();
  }
  var excluded = 'input, textarea, select, [contenteditable], [role="dialog"], [role="menu"], .focus-chip, .node-finder, .diagram-guide, .overview-map, .route-probe, .semantic-lens, .cm-panel, .diagram-nav';
  container.setAttribute('data-codemap-canvas', 'true');
  container.setAttribute('tabindex', '0');
  Archify.view.enableCodemap();
  container.addEventListener('wheel', function (event) {
    if (event.ctrlKey || event.metaKey || event.target.closest(excluded)) return;
    event.preventDefault();
    event.stopPropagation();
    close(false);
    var delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? container.clientHeight : 1);
    delta = Math.max(-100, Math.min(100, delta));
    Archify.view.zoomAt(Archify.view.state().scale * Math.exp(-delta * 0.002), event.clientX, event.clientY);
  }, { passive: false });
  container.addEventListener('contextmenu', function (event) {
    if (event.target.closest(excluded)) return;
    event.preventDefault();
    show(targetFor(event.target), event.clientX, event.clientY, event.target.closest('[tabindex]') || container);
  });
  var toolbar = container.querySelector('.diagram-nav');
  if (toolbar) {
    var more = document.createElement('button');
    more.type = 'button';
    more.textContent = '⋯';
    more.setAttribute('aria-label', '更多地图操作');
    more.title = '更多地图操作（Shift+F10）';
    more.addEventListener('click', function () { var rect = more.getBoundingClientRect(); show(selectedTarget(), rect.left, rect.top - 10, more); });
    toolbar.appendChild(more);
  }
  container.addEventListener('keydown', function (event) {
    if ((event.shiftKey && event.key === 'F10') || event.key === 'ContextMenu') {
      if (event.target.closest('input, textarea, select, [contenteditable]')) return;
      event.preventDefault();
      var rect = event.target.getBoundingClientRect();
      var target = targetFor(event.target);
      show(target.kind === 'canvas' ? selectedTarget() : target, rect.left + 20, rect.top + 20, event.target);
    }
  });
  menu.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' || event.key === 'Tab') { if (event.key === 'Escape') event.preventDefault(); close(true); return; }
    var buttons = Array.from(menu.querySelectorAll('button'));
    var index = buttons.indexOf(document.activeElement);
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].indexOf(event.key) < 0) return;
    event.preventDefault();
    var next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next].focus();
  });
  document.addEventListener('pointerdown', function (event) { if (!menu.contains(event.target)) close(false); });
  window.addEventListener('blur', function () { close(false); });
  window.addEventListener('resize', function () { close(false); });
  window.addEventListener('message', function (event) {
    if (!trusted(event)) return;
    var message = event.data;
    if (!message || message.source !== 'codemap' || message.type !== 'capabilities') return;
    // 独立本地文件没有认证维护宿主，不接收写入能力。
    var validContext = message.context && typeof message.context.repo_id === 'string' && typeof message.context.branch === 'string';
    capabilities = /^https?:$/.test(location.protocol) && validContext && Array.isArray(message.actions)
      ? message.actions.filter(function (id) { return id === 'create-requirement'; }) : [];
    hostContext = message.context && typeof message.context === 'object'
      ? { repo_id: message.context.repo_id, branch: message.context.branch } : {};
    close(false);
  });
  post({ type: 'ready', graph: graph.id });
})();
`;
