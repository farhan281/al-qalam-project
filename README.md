# Shamela Scraper — Project Documentation

## Ye Project Kya Hai?

Ye ek Python-based web scraper hai jo **shamela.ws** (Al-Maktaba Al-Shamela) se
Islamic books ka poora text automatically download karta hai.

Shamela duniya ki sabse badi Arabic Islamic digital library hai jisme
**10,000+** books hain — Quran tafseer, Hadith, Fiqh, Aqeedah wagera.

---

## Project Structure

```
shamela_project/
│
├── shamela_scraper.py       ← Main scraper (poora kaam yehi karta hai)
├── shamela_env/             ← Python virtual environment (dependencies)
│
└── shamela_output/          ← Scraper ka output (auto-create hota hai)
    ├── progress.json        ← Har book ka status track karta hai
    ├── report.csv           ← Tamam books ki summary CSV
    ├── العقيدة/
    │   ├── الفقه_الأكبر.txt
    │   └── كتاب_الأصنام.txt
    ├── الفقه/
    │   └── ...
    └── ...
```

---

## Kaise Kaam Karta Hai — Step by Step

### Step 1: Categories Fetch
```
shamela.ws (homepage)
    └── #cats section
        ├── العقيدة  (ID: 1)
        ├── الفقه    (ID: 2)
        ├── الحديث   (ID: 3)
        └── ... (42+ categories)
```
Script homepage parse karke tamam categories aur unke IDs nikaalti hai.

### Step 2: Books Fetch (Har Category Ke Liye)
```
shamela.ws/category/1
    └── book_title links
        ├── الفقه الأكبر   → /book/6388
        ├── كتاب الأصنام   → /book/6513
        └── ...
```

### Step 3: Book Page Fetch (Metadata Ke Liye)
```
shamela.ws/book/6388
    └── .betaka-index section
        ├── المؤلف: أبو حنيفة      ← author
        ├── الناشر: مكتبة الفرقان  ← publisher
        ├── الطبعة: الأولى          ← edition
        ├── عدد الصفحات: ١٦٧       ← total pages
        └── Table of Contents      ← topics
    └── breadcrumb: العقيدة        ← category
```

### Step 4: AJAX API Se Text Download
Shamela pages ek linked list ki tarah hain. Har page mein agla page ka ID hota hai:
```
GET /ajax/pageContent/6388/10001
Response JSON:
{
  "nass":    "<p>page text HTML</p>",
  "title":   "وحدانية الله تعالى",
  "pageNum": "١٤",
  "nextId":  "10002"    ← agla page; NULL agar last page
}

10001 → 10002 → 10003 → ... → NULL (book khatam)
```

### Step 5: Text File Save
```
الكتاب: الفقه الأكبر
الرابط: https://shamela.ws/book/6388
============================================================

--- ص14: وحدانية الله تعالى ---
وَالله تَعَالَى وَاحِد لَا من طَرِيق الْعدَد...

--- ص16: الصفات الذاتية والفعلية ---
اما الذاتية فالحياة وَالْقُدْرَة...
```

---

## Resume Feature — Kaise Kaam Karta Hai?

Agar internet cut ho ya Ctrl+C dabao to kaam barbaad nahi hota.

### progress.json mein partial book ki entry:
```json
"1_6388": {
  "title": "الفقه الأكبر",
  "pages": 45,
  "status": "partial",
  "next_page_id": 10046,
  "author": "أبو حنيفة",
  "total_pages": "١٦٧"
}
```

### Agli baar jab script chale:
1. progress.json load hota hai
2. `status == "partial"` dekhe to `next_page_id` se resume karta hai
3. Existing `.txt` file load karke us par append karta hai
4. Book complete hone par `status` → `"complete"` aur `next_page_id` hata deta hai

### Complete book skip condition:
```
status == "complete"  AND  pages_scraped >= total_pages
```
Dono conditions zaruri hain taaki purani galat entries dubara scrape hon.

---

## Retry Logic — Timeouts Ko Handle Karna

Shamela server kabhi kabhi slow hota hai ya timeout deta hai.
Scraper automatically retry karta hai:

```
Attempt 1 fail → wait 5s  → retry
Attempt 2 fail → wait 10s → retry
Attempt 3 fail → wait 15s → retry
Attempt 4 fail → wait 20s → retry
Attempt 5 fail → wait 25s → give up, save partial
```

Partial save hoti hai taaki resume ho sake.

---

## Terminal Output — Kya Dikhta Hai

```
📚 Fetching categories...
  ✅ 42 categories found

📁 العقيدة  —  38 books  (2 ✅ done, 36 to scrape)

  [OUTER BAR]  📁 العقيدة          ██████░░░░  1/42 categories [00:05<03:20]

  [BOOK BAR]   📚 الفقه الأكبر     ████░░░░░░ 12/36 books [05:20<16:00]

  [PAGE BAR]   ص27: القول في الصفات  ████████░░ 92/167 [00:45<01:20 1.2pg/s]

    ✅  الفقه الأكبر  (167 pages)
    ⚠️  كتاب الأصنام  (45 pages)   ← partial (timeout hua)
    ❌  Failed: ...                 ← completely fail
```

**3 nested bars:**
1. **Category bar** — overall kitni categories process huin
2. **Book bar** — is category mein kitni books huin
3. **Page bar** — current book ke kitne pages ho gaye (chapter title live update hota hai)

---

## Output Files

### 1. `shamela_output/<category>/<book_title>.txt`
Plain text file, UTF-8 encoded, Arabic text.

### 2. `shamela_output/progress.json`
```json
{
  "1_6388": {
    "title": "الفقه الأكبر",
    "pages": 167,
    "status": "complete",
    "author": "أبو حنيفة النعمان (ت ١٥٠هـ)",
    "publisher": "مكتبة الفرقان - الإمارات العربية",
    "edition": "الأولى، ١٤١٩هـ - ١٩٩٩م",
    "total_pages": "١٦٧",
    "topics": "بيان أصول الإيمان | وحدانية الله تعالى | ...",
    "category": "العقيدة"
  }
}
```
Key format: `{cat_id}_{book_id}`

### 3. `shamela_output/report.csv`
| Column | Description |
|---|---|
| category | Shamela category folder |
| book | Book title |
| book_id | Shamela book ID |
| author | Author with death year |
| publisher | Publisher name |
| edition | Edition and year |
| total_pages | Total printed pages (Arabic numerals) |
| pages_scraped | Pages actually scraped so far |
| status | `complete` or `partial` |
| topics | All chapter headings, pipe-separated |
| url | Shamela book URL |
| file | Local .txt file path |

---

## Kaise Chalayein

```bash
# Virtual environment activate karo
cd /home/ubuntu/shamela_project
source shamela_env/bin/activate

# Scraper chalao
python shamela_scraper.py

# Agar beech mein band karo aur dubara chalao — automatically resume hoga
python shamela_scraper.py
```

### Dependencies
```
requests        — HTTP requests
beautifulsoup4  — HTML parsing
tqdm            — Progress bars
```

Install:
```bash
pip install requests beautifulsoup4 tqdm
```

---

## Important Settings (`shamela_scraper.py` mein)

| Variable | Default | Matlab |
|---|---|---|
| `BASE_URL` | `https://shamela.ws` | Website ka address |
| `OUTPUT_DIR` | `shamela_output` | Output folder |
| `DELAY` | `1.5` seconds | Har book ke baad wait |
| `retries` | `5` | Har request ke liye max retries |
| `timeout` | `35` seconds | Request timeout |
| `time.sleep(0.3)` | 0.3 seconds | Pages ke beech delay |

`DELAY` kam karne se scraping fast hogi lekin server ban ka risk hai.

---

## Common Issues

| Error | Wajah | Fix |
|---|---|---|
| `ModuleNotFoundError: tqdm` | venv mein install nahi | `pip install tqdm` |
| `Read timed out` | Server slow hai | Auto-retry hoga, rukne ki zarurat nahi |
| Pages scraped < total pages | Pehle timeout hua tha | progress.json mein `status: partial` karo, dubara chalao |
| Arabic text garbled | Wrong encoding | File UTF-8 mein kholo |
