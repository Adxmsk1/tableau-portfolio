# Tableau portfolio

Three Tableau dashboards on sport, each built from data I collected and cleaned myself.

| | Question | Data | Shape |
|---|---|---|---|
| [chess](chess/) | Is chess getting younger? | FIDE rating lists, every January 2001-2026 | square, laid out on a chessboard |
| [running](running/) | What did super shoes do to marathon running? | World Athletics season top lists, 2001-2025 | long scroll, a marathon down the page |
| [ski-jumping](ski-jumping/) | Who rules the skies? | FIS World Cup results, 2001-2025 | landscape |

![Is chess getting younger?](chess/output/review.png)

To look at a dashboard without rebuilding anything, open the packaged workbook (`.twbx`) in each project's `tableau/`
folder in Tableau Desktop or Tableau Reader. Full-size screenshots are in each project's `output/` folder.

## Getting the data

None of these came as a tidy dataset, so most of the work was getting the data into shape:

- **Chess** - 26 annual rating list downloads from FIDE (over 100 MB in total). They're fixed-width text files and the
  layout changes over the years: columns move, and in 2010-12 two of the header labels run together ("TitlFed"). The
  parser reads the column positions from each year's header instead of hard-coding them.
- **Running** - around 49,000 marathon and half marathon performances scraped from World Athletics' season top lists,
  500 per event, sex and season.
- **Ski jumping** - around 43,000 World Cup results from 950+ races on the FIS website, working down from the
  calendar to each event and then each race. Result rows come in several shapes depending on the competition format,
  so the parser finds each jumper's birth year and nation first and works outwards from there.

Both scrapers cache every page they download and pause between requests, so they can be re-run without hitting the
sites again. The FIS one also retries when a request fails.

## How they're built

Each folder has the same steps:

1. `scripts/` - download or scrape the raw data, clean it, and shape it into the CSVs Tableau reads (`data/tableau`)
2. `scripts/text.py` - the commentary. The dashboards switch it with the same parameter as the charts (men/women, or
   the chosen nation for chess)
3. `tableau/build.py` - writes the workbook (`.twb`) and draws the background graphics with Pillow

`tableau_tools/twb.py` is a small helper for writing Tableau's workbook XML, and `gfx.py` holds the shared drawing bits.

## Checks and tests

`tableau_tools/check_outputs.py` checks the CSVs before they go into a workbook:

- every file each dashboard reads is there, has rows and has no duplicate rows
- no missing years - every season from 2001 for running and chess, and no gaps in either ski jumping World Cup
- every share or rate sits between 0 and 1
- every block of commentary has a title

`tests/` has pytest tests for the parsing (race times to seconds, the ski jumping result rows and race headers) and
for the checks themselves, including that they really do fail when a season goes missing.

## Running it

Python 3.11 or newer.

```
pip install -r requirements.txt
python tableau_tools/check_outputs.py
pytest
```

To rebuild one dashboard from scratch, for example chess:

```
python chess/scripts/download_fide.py
python chess/scripts/parse_fide.py
python chess/scripts/prepare_tableau.py
python chess/scripts/text.py
python chess/tableau/build.py
```

The raw downloads aren't in the repo (the FIDE lists alone are over 100 MB). Running the scripts fetches them again.

## Other projects

- [F1 budget cap](https://github.com/Adxmsk1/f1-budget-cap) - did the 2021 cost cap make Formula 1 more competitive?
  Jolpica F1 API, DuckDB, SQL data checks and Power BI.
- [Ibiza tourism economics](https://github.com/Adxmsk1/ibiza-tourism-economics) - Spain's INE statistics API, DuckDB
  and Power BI. Is Ibiza's hotel boom about more visitors or higher prices?
