// i18n.js: URLパス(/en/を含むか)からロケールを判定する
(function () {
  "use strict";
  window.LOCALE = location.pathname.includes("/en/") ? "en" : "ja";
  // 相対パスの基点。/en/配下のページから見て、data/やimg/などアプリ直下のファイルは1階層上になる
  window.ROOT = window.LOCALE === "en" ? "../" : "./";

  // heritage.jsonのdescriptionは英語のみ、descriptionJaは翻訳バッチで追加した日本語訳(未整備の場合は英語にフォールバック)
  window.pickDescription = function (site) {
    if (window.LOCALE === "ja" && site.descriptionJa) return site.descriptionJa;
    return site.description;
  };
})();
