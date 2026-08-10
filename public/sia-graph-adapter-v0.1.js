/* SIA-Infinity Hybrid Graph Adapter v0.1
 * ----------------------------------------
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Related engine: SIA Fibonacci-KNN v0.1 (symbolic, deterministic).
 * Priority:
 *   1. Cloudflare edge graph when configured by the repository manifest.
 *   2. Raw GitHub precomputed graph.
 *   3. Blogger JSON feed fallback.
 *
 * No paid AI API. No runtime dependency.
 */
(function (window, document) {
  'use strict';

  var VERSION = '0.1.0';
  var DEFAULTS = {
    graphUrl: '',
    graphUrls: [],
    edgeManifestUrl: '',
    relatedTarget: 'related-posts-list',
    statusTarget: 'sia-hybrid-status',
    currentLabelsTarget: 'post-labels-data',
    currentTitleSelector: '.post-title',
    maxRelated: 6,
    graphCacheMinutes: 30,
    edgeManifestCacheMinutes: 60,
    fallbackMaxResults: 40,
    minFallbackScore: 8
  };

  function extend(a, b) {
    var out = {}, k;
    for (k in a) if (Object.prototype.hasOwnProperty.call(a, k)) out[k] = a[k];
    for (k in b) if (Object.prototype.hasOwnProperty.call(b, k)) out[k] = b[k];
    return out;
  }

  function unique(items) {
    var seen = {}, out = [];
    (items || []).forEach(function (item) {
      var value = String(item || '').trim();
      if (!value || seen[value]) return;
      seen[value] = true;
      out.push(value);
    });
    return out;
  }

  function stripSlash(value) {
    return String(value || '').replace(/\/+$/, '');
  }

  var userConfig = window.SIA_CONFIG || {};
  var meta = document.querySelector('meta[name="sia-graph-url"]');
  if (!userConfig.graphUrl && meta && meta.content) userConfig.graphUrl = meta.content;
  var cfg = extend(DEFAULTS, userConfig);

  function cleanUrl(url) {
    try {
      var u = new URL(url, window.location.href);
      u.hash = '';
      u.search = '';
      return u.href.replace(/\/$/, '');
    } catch (e) {
      return String(url || '').split('#')[0].split('?')[0].replace(/\/$/, '');
    }
  }

  function hostnameOf(url) {
    try {
      return new URL(url, window.location.href).hostname.toLowerCase();
    } catch (e) {
      return '';
    }
  }

  function normalize(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/[\u200b-\u200d\ufeff]/g, '')
      .replace(/[,.!?;:()[\]{}"'“”‘’/\\|_\-]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function tokens(s) {
    var stop = {
      'the':1,'a':1,'an':1,'of':1,'in':1,'on':1,'for':1,'to':1,'and':1,'or':1,
      'but':1,'with':1,'from':1,'by':1,'at':1,'as':1,'is':1,'are':1,'was':1,
      'were':1,'be':1,'been':1,'this':1,'that':1,'these':1,'those':1,
      'your':1,'you':1,'we':1,'our':1,'best':1,'latest':1
    };
    return normalize(s).split(' ').filter(function (w) {
      return w.length > 1 && !stop[w];
    });
  }

  function setStatus(text, mode) {
    var el = document.getElementById(cfg.statusTarget);
    if (!el) return;
    el.textContent = text || '';
    if (mode) el.setAttribute('data-mode', mode);
  }

  function renderRelated(items, mode) {
    var list = document.getElementById(cfg.relatedTarget);
    if (!list) return;

    list.innerHTML = '';
    if (!items || !items.length) {
      list.innerHTML = '<li>No sufficiently relevant posts found.</li>';
      list.setAttribute('data-sia-mode', mode || 'unknown');
      return;
    }

    items.slice(0, cfg.maxRelated).forEach(function (item) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = item.url;
      a.textContent = item.title;
      if (item.score !== undefined) a.setAttribute('data-sia-score', item.score);
      if (item.reasons && item.reasons.length) {
        a.setAttribute('data-sia-reasons', item.reasons.join(','));
      }
      li.appendChild(a);
      list.appendChild(li);
    });

    list.setAttribute('data-sia-mode', mode || 'unknown');
  }

  function graphCacheKey(url) {
    return 'sia_graph_v01:' + url;
  }

  function manifestCacheKey(url) {
    return 'sia_edge_manifest_v01:' + url;
  }

  function readTimedCache(key, maxMinutes) {
    try {
      var raw = localStorage.getItem(key);
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (!obj || !obj.savedAt || obj.value === undefined) return null;
      if ((Date.now() - obj.savedAt) > maxMinutes * 60 * 1000) return null;
      return obj.value;
    } catch (e) {
      return null;
    }
  }

  function writeTimedCache(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify({ savedAt: Date.now(), value: value }));
    } catch (e) {}
  }

  function validateGraph(graph) {
    return !!(
      graph &&
      graph.sia &&
      graph.sia.format === 'sia-symbolic-graph' &&
      graph.posts &&
      typeof graph.posts === 'object'
    );
  }

  function graphMatchesCurrentBlog(graph) {
    var graphHost = graph && graph.sia ? hostnameOf(graph.sia.blog_url) : '';
    return !graphHost || graphHost === window.location.hostname.toLowerCase();
  }

  async function loadEdgeManifest() {
    if (!cfg.edgeManifestUrl) return null;

    var cached = readTimedCache(
      manifestCacheKey(cfg.edgeManifestUrl),
      cfg.edgeManifestCacheMinutes
    );
    if (cached) return cached;

    try {
      var response = await fetch(cfg.edgeManifestUrl, {
        method: 'GET',
        mode: 'cors',
        credentials: 'omit',
        cache: 'no-cache'
      });
      if (!response.ok) return null;
      var manifest = await response.json();
      if (!manifest || typeof manifest !== 'object') return null;
      writeTimedCache(manifestCacheKey(cfg.edgeManifestUrl), manifest);
      return manifest;
    } catch (e) {
      return null;
    }
  }

  async function candidateGraphUrls() {
    var urls = [];
    var manifest = await loadEdgeManifest();
    if (manifest && manifest.cloudflare_base_url) {
      urls.push(
        stripSlash(manifest.cloudflare_base_url) +
        '/graphs/' + window.location.hostname + '/sia-graph.json'
      );
    }

    if (Array.isArray(cfg.graphUrls)) urls = urls.concat(cfg.graphUrls);
    if (cfg.graphUrl) urls.push(cfg.graphUrl);
    return unique(urls);
  }

  async function loadGraphFromUrl(url) {
    var cached = readTimedCache(graphCacheKey(url), cfg.graphCacheMinutes);
    if (cached && validateGraph(cached) && graphMatchesCurrentBlog(cached)) {
      return cached;
    }

    var response = await fetch(url, {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      cache: 'no-cache'
    });
    if (!response.ok) throw new Error('graph-http-' + response.status);

    var graph = await response.json();
    if (!validateGraph(graph)) throw new Error('graph-invalid');
    if (!graphMatchesCurrentBlog(graph)) throw new Error('graph-blog-mismatch');

    writeTimedCache(graphCacheKey(url), graph);
    return graph;
  }

  function findGraphPost(graph) {
    var current = cleanUrl(window.location.href);
    var posts = graph.posts || {};
    var id, p;
    for (id in posts) {
      if (!Object.prototype.hasOwnProperty.call(posts, id)) continue;
      p = posts[id];
      if (p && cleanUrl(p.url) === current) return { id: id, post: p };
    }
    return null;
  }

  async function loadCurrentGraph() {
    var urls = await candidateGraphUrls();
    if (!urls.length) throw new Error('graph-url-not-configured');

    var errors = [];
    for (var i = 0; i < urls.length; i++) {
      try {
        var graph = await loadGraphFromUrl(urls[i]);
        var current = findGraphPost(graph);
        if (!current) {
          errors.push('current-post-not-in-graph');
          continue;
        }
        return {
          graph: graph,
          current: current,
          url: urls[i],
          source: i === 0 && urls.length > 1 ? 'edge' : 'github'
        };
      } catch (e) {
        errors.push(e && e.message ? e.message : String(e));
      }
    }
    throw new Error(errors.join('|') || 'graph-unavailable');
  }

  function hydrateGraphRelated(graph, current) {
    var posts = graph.posts || {};
    var refs = current.post.related || [];
    var out = [];

    refs.forEach(function (ref) {
      var p = posts[ref.id];
      if (!p || !p.url || cleanUrl(p.url) === cleanUrl(window.location.href)) return;
      out.push({
        id: ref.id,
        title: p.title || 'Untitled',
        url: p.url,
        score: ref.score,
        reasons: ref.reasons || []
      });
    });

    return out;
  }

  function currentTitle() {
    var el = document.querySelector(cfg.currentTitleSelector);
    return el ? (el.textContent || '').trim() : document.title;
  }

  function currentLabels() {
    var el = document.getElementById(cfg.currentLabelsTarget);
    if (!el) return [];
    return (el.textContent || '')
      .split(',')
      .map(function (x) { return x.trim(); })
      .filter(Boolean);
  }

  function entryToPost(entry) {
    var link = (entry.link || []).find(function (x) { return x.rel === 'alternate'; });
    return {
      title: entry.title && entry.title.$t ? entry.title.$t : 'Untitled',
      url: link ? link.href : '',
      labels: (entry.category || []).map(function (c) { return c.term || ''; }).filter(Boolean)
    };
  }

  function fallbackScore(post, ctx) {
    // Fibonacci-KNN Lite: the browser fallback has labels/title but no
    // precomputed entity graph, so it preserves the same ordering philosophy.
    var reasons = ['fibonacci_knn_fallback'];
    var candidateLabels = (post.labels || []).map(normalize).filter(Boolean);
    var ctxLabels = ctx.labels.map(normalize).filter(Boolean);

    var primaryMatch = !!(
      ctxLabels.length && candidateLabels.length &&
      ctxLabels[0] === candidateLabels[0]
    );

    var labelUnion = {};
    ctxLabels.forEach(function (x) { labelUnion[x] = true; });
    candidateLabels.forEach(function (x) { labelUnion[x] = true; });
    var sharedLabels = ctxLabels.filter(function (x) {
      return candidateLabels.indexOf(x) !== -1;
    });
    var labelSimilarity = Object.keys(labelUnion).length
      ? sharedLabels.length / Object.keys(labelUnion).length
      : 0;

    var a = tokens(ctx.title);
    var b = tokens(post.title);
    var tokenUnion = {};
    a.forEach(function (x) { tokenUnion[x] = true; });
    b.forEach(function (x) { tokenUnion[x] = true; });
    var bSet = {};
    b.forEach(function (x) { bSet[x] = true; });
    var sharedTitle = a.filter(function (x) { return bSet[x]; });
    var titleSimilarity = Object.keys(tokenUnion).length
      ? sharedTitle.length / Object.keys(tokenUnion).length
      : 0;

    var weighted =
      (primaryMatch ? 21 : 0) +
      (8 * labelSimilarity) +
      (13 * titleSimilarity);
    var score = (weighted / 42) * 100;

    if (primaryMatch) reasons.push('same_silo');
    if (labelSimilarity) reasons.push('shared_label');
    if (titleSimilarity) reasons.push('title_pattern');

    return { score: Math.round(score * 1000) / 1000, reasons: reasons };
  }

  async function fetchLabelPosts(label) {
    var url = '/feeds/posts/default/-/' + encodeURIComponent(label) +
      '?alt=json&max-results=' + cfg.fallbackMaxResults;
    var res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) throw new Error('fallback-feed');
    var data = await res.json();
    var entries = data && data.feed && Array.isArray(data.feed.entry) ? data.feed.entry : [];
    return entries.map(entryToPost);
  }

  async function fallbackRelated() {
    var ctx = { title: currentTitle(), labels: currentLabels() };
    var batches = [];

    if (ctx.labels.length) {
      for (var i = 0; i < Math.min(4, ctx.labels.length); i++) {
        try {
          batches.push(await fetchLabelPosts(ctx.labels[i]));
        } catch (e) {}
      }
    }

    if (!batches.length) {
      try {
        var res = await fetch(
          '/feeds/posts/default?alt=json&max-results=' + cfg.fallbackMaxResults,
          { credentials: 'same-origin' }
        );
        if (res.ok) {
          var data = await res.json();
          var entries = data && data.feed && Array.isArray(data.feed.entry) ? data.feed.entry : [];
          batches.push(entries.map(entryToPost));
        }
      } catch (e) {}
    }

    var byUrl = {};
    batches.flat().forEach(function (p) {
      var key = cleanUrl(p.url);
      if (key && key !== cleanUrl(window.location.href) && !byUrl[key]) byUrl[key] = p;
    });

    return Object.keys(byUrl).map(function (key) {
      var p = byUrl[key];
      var s = fallbackScore(p, ctx);
      return { title: p.title, url: p.url, score: s.score, reasons: s.reasons };
    }).filter(function (x) {
      return x.score >= cfg.minFallbackScore;
    }).sort(function (a, b) {
      return b.score - a.score || a.title.localeCompare(b.title);
    }).slice(0, cfg.maxRelated);
  }

  async function boot() {
    if (!document.getElementById(cfg.relatedTarget)) return;

    try {
      setStatus('Loading SIA precomputed intelligence...', 'loading');
      var loaded = await loadCurrentGraph();
      var items = hydrateGraphRelated(loaded.graph, loaded.current);
      var mode = loaded.source === 'edge' ? 'precomputed-edge' : 'precomputed-github';

      renderRelated(items, mode);
      setStatus(
        loaded.source === 'edge' ? 'SIA Cloudflare Edge Intelligence' : 'SIA GitHub Intelligence',
        mode
      );

      window.dispatchEvent(new CustomEvent('sia:hybrid-ready', {
        detail: {
          mode: mode,
          version: VERSION,
          graphUrl: loaded.url,
          currentPostId: loaded.current.id,
          related: items
        }
      }));
      return;
    } catch (e) {
      console.warn('[SIA v0.1] Precomputed sources unavailable, using Blogger fallback:', e.message || e);
    }

    try {
      setStatus('Blogger fallback intelligence...', 'fallback-loading');
      var fallback = await fallbackRelated();
      renderRelated(fallback, 'fallback');
      setStatus('SIA Blogger Fallback Mode', 'fallback');

      window.dispatchEvent(new CustomEvent('sia:hybrid-ready', {
        detail: { mode: 'fallback', version: VERSION, related: fallback }
      }));
    } catch (e2) {
      console.warn('[SIA v0.1] Fallback failed:', e2);
      setStatus('SIA related engine unavailable', 'error');
    }
  }

  window.SIAHybrid = {
    version: VERSION,
    config: cfg,
    boot: boot,
    candidateGraphUrls: candidateGraphUrls,
    loadCurrentGraph: loadCurrentGraph,
    fallbackRelated: fallbackRelated
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(window, document);
