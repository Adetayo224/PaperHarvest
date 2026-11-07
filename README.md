# PaperHarvest

Download recent open access research papers on any topic, straight into your folder, from a simple browser interface.

Type your name, describe your research, choose how many papers you want and the earliest publication year, then click **Start downloading**. PaperHarvest searches the free [OpenAlex](https://openalex.org) index (which covers IEEE, Elsevier, Springer, MDPI, Wiley, arXiv and many more), picks papers that have a legal open access PDF, and saves them for you.

It was first built to collect 100 recent papers for a UAV systems literature review, and it works for any field.

## Features

* Clean local web interface that opens in your browser
* Choose your topic, the number of papers and the starting year
* Option to keep only peer reviewed papers and skip preprints
* Live progress bar and download log, with a Stop button
* Files named clearly, for example `001 2024 Deep Reinforcement Learning for UAV Navigation.pdf`
* A `Paper List.csv` with title, authors, year, venue, citations and DOI for every paper, useful for reference managers and PRISMA reviews
* No installs: uses only the Python standard library

## Requirements

Python 3.8 or newer. Nothing else.

## Quick start

```bash
git clone https://github.com/Adetayo224/PaperHarvest.git
cd "path/to/your/research folder"
python3 /path/to/PaperHarvest/paperharvest.py
```

Your browser opens at `http://127.0.0.1:8765`. Papers are saved inside a `Papers` folder in whichever folder you ran the command from, grouped by topic:

```
your research folder/
  Papers/
    GNSS denied UAV navigation/
      001 2023 ....pdf
      002 2024 ....pdf
      Paper List.csv
```

Press `Ctrl+C` in the terminal to close it.

If port 8765 is busy:

```bash
PAPERHARVEST_PORT=8800 python3 paperharvest.py
```

## Tips for better results

* Use focused keywords, for example `federated learning UAV` instead of a full sentence.
* Run several searches, one for each section of your review. Each topic gets its own folder.
* If fewer papers arrive than you asked for, try broader keywords or an earlier start year.

## Limitations

PaperHarvest downloads **only open access papers**. It does not bypass paywalls. Papers behind subscriptions (many IEEE Xplore or ScienceDirect articles) are skipped, so get those through your library or institution.

## Contributing

Issues and pull requests are welcome.

## Author

Saka Adetayo Muhammed, Samfred Robotics, Ogbomoso, Nigeria
[Portfolio](https://adetayosaka.vercel.app/) · [YouTube](https://www.youtube.com/@samfred_robotics)

## License

MIT
