// strings.js: 日本語/英語のUI文言辞書(app.jsが動的に描画する部分のみ)。LOCALEに応じてSオブジェクトの値が決まる。
(function () {
  "use strict";
  var en = window.LOCALE === "en";

  window.S = {
    categoryLabel: {
      Cultural: en ? "Cultural Heritage" : "文化遺産",
      Natural: en ? "Natural Heritage" : "自然遺産",
      Mixed: en ? "Mixed Heritage" : "複合遺産",
    },
    dangerCategoryLabel: function (categoryLabel) {
      return en ? "⚠ In Danger ・ " + categoryLabel : "⚠ 危機遺産 ・ " + categoryLabel;
    },
    meta: function (country, year) {
      var y = year == null ? (en ? "unknown" : "?") : year;
      return en ? country + " ・ Inscribed " + y : country + " ・ " + y + "年登録";
    },
    markVisited: en ? "Mark as visited" : "訪問済みにする",
    visited: en ? "✓ Visited" : "✓ 訪問済み",
    play: en ? "Play" : "再生",
    pause: en ? "Pause" : "一時停止",
    yearLabel: function (year) {
      return en ? String(year) : year + "年";
    },
    countLabel: function (visible, total) {
      return en ? "Showing " + visible + " / " + total : "表示中 " + visible + " / " + total;
    },
    fetchError: function (status) {
      return en
        ? "Failed to load heritage.json (status: " + status + ")"
        : "heritage.json の読み込みに失敗しました (status: " + status + ")";
    },
    loadError: en
      ? "Failed to load data. Please reload the page."
      : "データの読み込みに失敗しました。ページを再読み込みしてください。",
  };
})();
