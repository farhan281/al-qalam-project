# Category-Specific Run Scripts

This folder contains 40 auto-generated Python scripts, one for each Shamela category.

## Usage

### Run all categories (from project root):
```bash
cd ..
python run.py
```

### Run a specific category:

**Option 1: Use the main script with --cat argument**
```bash
cd ..
python run.py --cat 1        # العقيدة
python run.py --cat 14       # الفقه الحنفي
python run.py --cat 25       # التاريخ
```

**Option 2: Run the category script directly**
```bash
python scripts/1_العقيدة.py
python scripts/14_الفقه_الحنفي.py
```

## Category List

| ID | Category Name | Script |
|----|---|---|
| 1 | العقيدة | `1_العقيدة.py` |
| 2 | الفرق والردود | `2_الفرق_andالردandد.py` |
| 3 | التفسير | `3_التفسير.py` |
| 4 | علوم القرآن وأصول التفسير | `4_علandم_القرآن_andأصandل_التفسير.py` |
| 5 | التجويد والقراءات | `5_التجandيد_andالقراءات.py` |
| 6 | كتب السنة | `6_كتب_السنة.py` |
| 7 | شروح الحديث | `7_شرandح_الحديث.py` |
| 8 | التخريج والأطراف | `8_التخريج_andالأطراف.py` |
| 9 | العلل والسؤلات الحديثية | `9_العلل_andالسؤلات_الحديثية.py` |
| 10 | علوم الحديث | `10_علandم_الحديث.py` |
| 11 | أصول الفقه | `11_أصandل_الفقه.py` |
| 12 | علوم الفقه والقواعد الفقهية | `12_علandم_الفقه_andالقandاعد_الفقهية.py` |
| 13 | المنطق | `13_المنطق.py` |
| 14 | الفقه الحنفي | `14_الفقه_الحنفي.py` |
| 15 | الفقه المالكي | `15_الفقه_المالكي.py` |
| 16 | الفقه الشافعي | `16_الفقه_الشافعي.py` |
| 17 | الفقه الحنبلي | `17_الفقه_الحنبلي.py` |
| 18 | الفقه العام | `18_الفقه_العام.py` |
| 19 | مسائل فقهية | `19_مسائل_فقهية.py` |
| 20 | السياسة الشرعية والقضاء | `20_السياسة_الشرعية_andالقضاء.py` |
| 21 | الفرائض والوصايا | `21_الفرائض_andالandصايا.py` |
| 22 | الفتاوى | `22_الفتاandى.py` |
| 23 | الرقائق والآداب والأذكار | `23_الرقائق_andالآداب_andالأذكار.py` |
| 24 | السيرة النبوية | `24_السيرة_النبandية.py` |
| 25 | التاريخ | `25_التاريخ.py` |
| 26 | التراجم والطبقات | `26_التراجم_andالطبقات.py` |
| 27 | الأنساب | `27_الأنساب.py` |
| 28 | البلدان والرحلات | `28_البلدان_andالرحلات.py` |
| 29 | كتب اللغة | `29_كتب_اللغة.py` |
| 30 | الغريب والمعاجم | `30_الغريب_andالمعاجم.py` |
| 31 | النحو والصرف | `31_النحand_andالصرف.py` |
| 32 | الأدب | `32_الأدب.py` |
| 33 | العروض والقوافي | `33_العرandض_andالقandافي.py` |
| 34 | الشعر ودواوينه | `34_الشعر_andدandaandينه.py` |
| 35 | البلاغة | `35_البلاغة.py` |
| 36 | الجوامع | `36_الجandامع.py` |
| 37 | فهارس الكتب والأدلة | `37_فهارس_الكتب_andالأدلة.py` |
| 38 | الطب | `38_الطب.py` |
| 39 | كتب عامة | `39_كتب_عامة.py` |
| 40 | علوم أخرى | `40_علandم_أخرى.py` |

## Notes

- Each category script runs independently and scrapes books in that category only.
- Progress is saved in `shamela_output/progress.json` regardless of which script you run.
- Category-specific CSV reports are generated in `shamela_output/reports/<category>.csv`.
- Book files are saved in `shamela_output/<category>/` folders.
- Resume works across all scripts — if interrupted, restart the same script to continue from the last saved page.
- No duplicates: each book is tracked by `category_id_book_id` key in progress.json.

## Parallel Execution

You can run multiple categories in parallel in separate terminals:

```bash
# Terminal 1
python run.py --cat 1

# Terminal 2
python run.py --cat 14

# Terminal 3
python run.py --cat 25
```

All runs share the same `shamela_output/progress.json` and `shamela_output/reports/`, so books won't be duplicated across runs.
