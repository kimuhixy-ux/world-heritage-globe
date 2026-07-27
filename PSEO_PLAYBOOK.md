# 世界遺産データ向けプログラマティックSEO運用手順

`world-heritage-globe` の日英静的世界遺産ページを再生成・検証するための手順書です。生成ページは既存の3D地球儀アプリを置き換えず、検索結果から事実情報とアプリ本体へ案内します。

## 対象データとURL

- 入力: `data/heritage.json` 1,258件
- 日本語: `/items/<id-name>/`
- 英語: `/en/items/<id-name>/`

slugは世界遺産IDと英語名から生成する。IDを含めることで名称変更時の識別性と一意性を確保し、重複があれば生成を停止する。

## 出力範囲

静的ページには名称、所在国、地域、分類、登録年、危機遺産の該当状況、緯度・経度、出典URL、YouTube検索リンクだけを掲載する。

`description` / `descriptionJa` の出典説明文、画像、映像は、本文、title、description、OGP、JSON-LD、索引へ転載しない。検証スクリプトは説明文の混入を全ページで検査する。また、公認・提携を示唆しない独立運営の索引である旨を明記する。

## 構造化データ

- 世界遺産: `TouristAttraction`
- 座標: `GeoCoordinates`
- 所在国: `PostalAddress`
- 分類・登録年・地域・危機遺産: `PropertyValue`
- 共通: `WebSite`、`BreadcrumbList`

登録基準、公式な法的地位、最新の危機遺産状態など、入力データにない情報を推測しない。検索メタ情報では公認を連想させる表現を使わない。

## 多言語・広告・OGP

日英ページにcanonicalと `ja` / `en` / `x-default` hreflangを相互設定する。OGPとTwitter Cardには共通の `icons/icon-512.png` を使用する。

既存と同じ本番ホスト判定でAdSense ID `ca-pub-3562055879455682` を読み込む。生成ページをService Workerの事前キャッシュには追加せず、`/items/` のHTMLナビゲーションをネットワーク優先にする。

## sitemap

1,258件×2言語、索引2ページ、既存主要6ページの合計2,524 URLを単一 `sitemap.xml` に収録する。5万URLを超えるサイトへ展開する場合はsitemapを分割する。`robots.txt` からsitemapの絶対URLを案内する。

## 再生成と検証

```sh
python3 scripts/generate_pages.py
python3 scripts/validate_generated_pages.py
git diff --check
```

生成された `items/` と `en/items/` は手編集しない。入力データ、テンプレート、生成スクリプトを修正して再生成する。

## 公開前チェック

- [ ] 日英各1,258詳細ページと索引2ページがある
- [ ] titleとdescriptionが各言語内で一意
- [ ] canonical、相互hreflang、OGP、JSON-LDが正しい
- [ ] 出典説明文と画像が生成ページに含まれない
- [ ] 公認・提携を示唆するSEO表現がない
- [ ] 全内部リンクの参照先が存在する
- [ ] sitemapが2,524 URLで重複なし
- [ ] 生成ページが事前キャッシュ対象外
- [ ] git push前にオーナーの承認を得る
