# IELTS WordList Generator

## Purpose

Given English words, generate one valid JSON WordList for this IELTS vocabulary-review application. Focus on useful IELTS meanings and usage rather than complete dictionary coverage.

## Required structure

Each Word contains:

- `wid`: unique lowercase Word ID. Normally derive it from the English word using simple lowercase letters, digits, and `_`; replace spaces or punctuation separators with `_`. Keep it short and stable. If two words would produce the same `wid`, add a short numeric suffix such as `_2`.
- `word`: original English word.
- `phonetic`: common IPA pronunciation.
- `senses`: one or more IELTS-relevant senses.
- `notes`: optional Word-level learning notes. Keep useful usage advice brief. When the word has a clear, reliable, and memory-worthy root/etymology, `notes` may also explain the root/origin and semantic development; otherwise do not force etymology and use `""` when there is nothing useful to add.

Each sense contains:

- `pos`: part of speech such as `n.`, `v.`, `adj.`, `adv.`.
- `english_meaning`: concise English definition. It may be `""` when an English definition is unavailable.
- `chinese_meaning`: concise Chinese meaning for this sense.
- `eid`: Example ID for this English example. When `example` is non-empty, `eid` must contain exactly 6 random digits, for example `501372`. Digits may start with `0`, so always keep `eid` as a string rather than a JSON number.
- `example`: natural IELTS-level English example sentence.
- `example_translation`: accurate Chinese translation of the example.
- `synonyms`: useful IELTS synonyms or near-synonyms for this specific sense. Use 0 to 5 items. When accurate, common IELTS-relevant alternatives exist, include as many useful ones as possible up to 5; accuracy is more important than quantity.
- `collocations`: common and useful collocations.

## ID rules

1. Every `wid` must be unique within the WordList.
2. Every visible `word` must also be unique within the WordList, ignoring letter case. Put multiple meanings of the same spelling under one Word's `senses` instead of creating duplicate Word entries.
3. Every non-empty `eid` must be unique within the entire WordList.
4. Generate `eid` as a JSON string containing exactly 6 random digits whenever an English `example` is generated.
5. While generating the WordList, keep a temporary `used_eids` set. If a newly generated `eid` is already in the set, generate another six-digit value until it is unique, then add it to the set.
6. If an English `example` is regenerated or replaced, generate a new `eid` at the same time.
7. If only `example_translation` changes and the English `example` itself does not change, keep the existing `eid`.
8. If `example` is empty or absent, `eid` may be absent or `""`; these are the only normal states for a sense without an example.
9. If a sense has an English example but `eid` is missing or empty, append a brief data warning to the Word-level `notes`, such as `数据提示：sense 2 例句缺少 eid。`
10. If a sense has an English example but its non-empty `eid` is not exactly 6 digits, append a brief data warning such as `数据提示：sense 2 例句 eid 无效。`
11. If a sense has no English example but has a non-empty `eid`, append a brief data warning such as `数据提示：sense 2 无例句但存在 eid。`
12. Data warnings are appended to existing `notes`; never overwrite useful original notes.

## Notes and etymology rules

1. Root/etymology information belongs in the Word-level `notes` field. Do not add a separate `etymology` field and do not repeat the same etymology inside individual senses.
2. Etymology is optional. Add it only when the origin is reasonably clear and reliable, and when it genuinely helps the learner understand or remember the modern word. Do not add etymology merely to fill `notes`.
3. Prefer concise development chains such as: `词源：trans-（穿过）+ 拉丁语 portare（携带）→“携带到另一边”→“运送；运输”。` The useful pattern is **root/source → original meaning → semantic development → modern meaning**, not a bare list of roots.
4. When the historical source language or form is known and useful, identify it briefly (for example Latin or Greek), but keep the explanation compact and learner-oriented rather than encyclopedic.
5. Do not invent roots from superficial spelling, use folk etymologies as facts, or guess disputed/uncertain origins. If the origin cannot be stated with reasonable confidence, omit the etymology.
6. Prioritize etymology for words where morphology or semantic history creates a useful memory link, such as clear prefix/root combinations, productive Latin/Greek roots, or a meaningful shift from the original sense to the modern IELTS-relevant sense. Ordinary words whose historical origin adds little learning value do not need etymology.
7. `notes` may combine a short etymology with another genuinely useful usage note. Keep both concise. If data warnings are required by the ID rules, append them after the useful notes rather than replacing them.

### Etymology note example

```json
"notes": "词源：trans-（穿过）+ 拉丁语 portare（携带）→“携带到另一边”→“运送；运输”。"
```

## Content rules

1. Prefer meanings commonly useful in IELTS reading, writing, listening, or speaking.
2. Do not add rare meanings merely to make an entry comprehensive.
3. Put different important meanings or parts of speech in separate `senses`.
4. Keep `english_meaning` clear and concise. Prefer common English words and do not define the target word by simply repeating it.
5. Keep `chinese_meaning` accurate and concise.
6. Examples should be natural and academically appropriate, not artificially complicated.
7. `example_translation` should translate the example directly without extra explanation.
8. Synonyms and collocations should be genuinely useful in real IELTS contexts. `synonyms` may be empty, but must contain no more than 5 items. Prefer accurate, common synonyms or near-synonyms for the current sense and part of speech; when several good options exist, include as many useful ones as possible up to 5. Never add weak, rare, or mismatched alternatives merely to increase the count.
9. Keep `notes` brief and practical.
10. Do not generate review counts, study status, or other user-learning data.
11. Do not append the number of words to the WordList `name`, and do not add a redundant `word_count` field. Keep `name` focused on the vocabulary theme. If the user explicitly requests a target number or range of words, honor that request without encoding the count in `name`.
12. Keep `schema_version` equal to `1`.
13. Output valid JSON only when the user asks for a WordList data file.

## Canonical JSON structure example

Use this example as the structural template for generated WordLists. Keep the field names, nesting, and data types unless another rule in this Skill explicitly permits an optional/empty value.

```json
{
  "schema_version": 1,
  "name": "IELTS Education Vocabulary",
  "description": "雅思教育类常用词汇",
  "words": [
    {
      "wid": "address",
      "word": "address",
      "phonetic": "/əˈdres/",
      "senses": [
        {
          "pos": "v.",
          "english_meaning": "to deal with or take action on a problem or difficult situation",
          "chinese_meaning": "处理；应对，尤指问题或困难",
          "eid": "482731",
          "example": "Governments should address the underlying causes of educational inequality.",
          "example_translation": "政府应当解决教育不平等的根本原因。",
          "synonyms": ["tackle", "deal with", "confront", "handle"],
          "collocations": ["address a problem", "address an issue", "address concerns"]
        },
        {
          "pos": "n.",
          "english_meaning": "the details of where a person lives or an organization is located",
          "chinese_meaning": "地址；住址",
          "eid": "105964",
          "example": "Applicants must provide a current address on the registration form.",
          "example_translation": "申请人必须在登记表上提供当前地址。",
          "synonyms": [],
          "collocations": ["home address", "postal address", "current address"]
        }
      ],
      "notes": "IELTS 写作中常作动词使用。"
    }
  ]
}
```
