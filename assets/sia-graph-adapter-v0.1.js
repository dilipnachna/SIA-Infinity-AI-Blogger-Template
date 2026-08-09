/* SIA-Infinity Hybrid Graph Adapter v0.1
 * ----------------------------------------
 * Precomputed mode:
 *   Fetches sia-graph.json and uses precomputed related relationships.
 *
 * Fallback mode:
 *   If graph is unavailable / invalid / current post not found,
 *   uses Blogger JSON feed + labels/title for lightweight scoring.
 *
 * No paid API. No dependency.
 */
(function (window, document) {
  'use strict';

  var VERSION = '0.1.0';
  var DEFAULTS = {
    graphUrl: '',
    relatedTarget: 'related-posts-list',
    statusTarget: 'sia-hybrid-status',
    currentLabelsTarget: 'post-labels-data',
    currentTitleSelector: '.post-title',
    maxRelated: 6,
    graphCacheMinutes: 360,
    fallbackMaxResults: 40,
    minFallbackScore: 8
  };

  function extend(a, b) {
    var out = {}, k;
    for (k in a) if (Object.prototype.hasOwnProperty.call(a, k)) out[k] = a[k];
    for (k in b) if (Object.prototype.hasOwnProperty.call(b, k)) out[k] = b[k];
    return out;
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

  function cacheKey(url) {
    return 'sia_graph_v01:' + url;
  }

  function getCachedGraph(url) {
    try {
      var raw = localStorage.getItem(cacheKey(url));
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (!obj || !obj.savedAt || !obj.graph) return null;
      var age = Date.now() - obj.savedAt;
      if (age > cfg.graphCacheMinutes * 60 * 1000) return null;
      return obj.graph;
    } catch (e) {
      return null;
    }
  }

  function saveCachedGraph(url, graph) {
    try {
      localStorage.setItem(cacheKey(url), JSON.stringify({
        savedAt: Date.now(),
        graph: graph
      }));
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

  async function loadGraph() {
    if (!cfg.graphUrl) throw new Error('graph-url-not-configured');

    var cached = getCachedGraph(cfg.graphUrl);
    if (cached && validateGraph(cached)) return cached;

    var response = await fetch(cfg.graphUrl, {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      cache: 'no-cache'
    });
    if (!response.ok) throw new Error('graph-http-' + response.status);

    var graph = await response.json();
    if (!validateGraph(graph)) throw new Error('graph-invalid');

    saveCachedGraph(cfg.graphUrl, graph);
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

  function hydrateGraphRelated(graph, current) {
    var posts = graph.posts || {};
    var refs = (current.post.related || []);
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
    var score = 0;
    var reasons = [];
    var candidateLabels = (post.labels || []).map(normalize);
    var ctxLabels = ctx.labels.map(normalize);

    var sharedLabels = ctxLabels.filter(function (x) {
      return candidateLabels.indexOf(x) !== -1;
    });
    if (sharedLabels.length) {
      score += 14 + Math.min(12, (sharedLabels.length - 1) * 4);
      reasons.push('shared_label');
    }

    var a = tokens(ctx.title);
    var b = tokens(post.title);
    var bSet = {};
    b.forEach(function (x) { bSet[x] = true; });
    var overlap = a.filter(function (x) { return bSet[x]; }).length;

    if (overlap) {
      score += overlap * 5;
      reasons.push('title_overlap');
    }

    return { score: score, reasons: reasons };
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
    var ctx = {
      title: currentTitle(),
      labels: currentLabels()
    };

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

    var ranked = Object.keys(byUrl).map(function (key) {
      var p = byUrl[key];
      var s = fallbackScore(p, ctx);
      return {
        title: p.title,
        url: p.url,
        score: s.score,
        reasons: s.reasons
      };
    }).filter(function (x) {
      return x.score >= cfg.minFallbackScore;
    }).sort(function (a, b) {
      return b.score - a.score || a.title.localeCompare(b.title);
    });

    return ranked.slice(0, cfg.maxRelated);
  }

  async function boot() {
    if (!document.getElementById(cfg.relatedTarget)) return;

    if (cfg.graphUrl) {
      try {
        setStatus('Loading precomputed intelligence…', 'loading');
        var graph = await loadGraph();
        var current = findGraphPost(graph);
        if (!current) throw new Error('current-post-not-in-graph');

        var items = hydrateGraphRelated(graph, current);
        renderRelated(items, 'precomputed');
        setStatus('SIA Precomputed Intelligence', 'precomputed');

        window.dispatchEvent(new CustomEvent('sia:hybrid-ready', {
          detail: {
            mode: 'precomputed',
            version: VERSION,
            currentPostId: current.id,
            related: items
          }
        }));
        return;
      } catch (e) {
        console.warn('[SIA v0.1] Precomputed mode unavailable, using fallback:', e.message || e);
      }
    }

    try {
      setStatus('Blogger fallback intelligence…', 'fallback-loading');
      var fallback = await fallbackRelated();
      renderRelated(fallback, 'fallback');
      setStatus('SIA Blogger Fallback Mode', 'fallback');

      window.dispatchEvent(new CustomEvent('sia:hybrid-ready', {
        detail: {
          mode: 'fallback',
          version: VERSION,
          related: fallback
        }
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
    loadGraph: loadGraph,
    fallbackRelated: fallbackRelated
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})(window, document);
