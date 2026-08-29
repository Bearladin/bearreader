const TARGET_URL = "__BASE_ORIGIN__";
const PREFIX_URL = "__BROWSE_PREFIX__";

(function () {
  const name = "___LNCRAWL_INTERCEPTOR___";
  if (window[name]) return;
  window[name] = this;

  function wrap(url) {
    if (!url) return url;
    const s = String(url);
    if (s.startsWith(PREFIX_URL)) {
      return s;
    } else if (s.startsWith("/") && !s.startsWith("//")) {
      return PREFIX_URL + "/" + TARGET_URL + s;
    }
    return PREFIX_URL + "/" + s;
  }

  // Intercept XHR
  const _open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    return _open.call(this, method, wrap(url), ...rest);
  };

  // Intercept fetch
  const _fetch = window.fetch;
  window.fetch = function (input, init) {
    if (typeof input === "string") {
      input = wrap(input);
    } else if (input instanceof Request) {
      input = new Request(wrap(input.url), input);
    }
    return _fetch.call(this, input, init);
  };

  const ATTRS = {
    A: "href",
    FORM: "action",
    IMG: "src",
    SCRIPT: "src",
    LINK: "href",
    IFRAME: "src",
    SOURCE: "src",
  };

  function rewriteNode(node) {
    if (!(node instanceof Element)) return;
    const attr = ATTRS[node.tagName];
    if (attr) {
      const val = node.getAttribute(attr);
      if (val) node.setAttribute(attr, wrap(val));
    }
    for (const [tag, a] of Object.entries(ATTRS)) {
      for (const el of node.querySelectorAll(tag.toLowerCase())) {
        const val = el.getAttribute(a);
        if (val) el.setAttribute(a, wrap(val));
      }
    }
  }

  rewriteNode(document);

  function onMutation(mutations) {
    for (const { addedNodes } of mutations) {
      for (const node of addedNodes) {
        rewriteNode(node);
      }
    }
  }

  const observer = new MutationObserver(onMutation);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
