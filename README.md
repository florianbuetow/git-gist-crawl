# Gist Crawl

Automated GitHub repository crawler to generate LLM context data. It generates comprehensive gists using gitingest.com. Clones repos, tracks changes, and regenerates gists only when updates are detected.

## Features

- **Smart Updates**: Only regenerates gists when repository changes are detected via git pull
- **Batch Processing**: Process multiple repositories from a queue file
- **State Tracking**: Maintains crawl history to avoid unnecessary re-processing
- **Organized Storage**: Clean directory structure separating cloned code and generated gists

## Requirements

- Python 3.10+
- `uv` package manager
- Git
- Google Chrome

## Installation

```bash
make init
```

This will:
- Install Python dependencies (selenium)
- Create the data directory

## Usage

### 1. Add Repositories to Queue

Edit `crawl-jobs.txt` and add GitHub repository URLs (one per line):

```
https://github.com/coderamp-labs/gitingest
https://github.com/anthropics/anthropic-sdk-python
```

Lines starting with `#` are comments and will be ignored.

### 2. Run Crawler

```bash
make crawl
```

The crawler will:
- Clone repositories to `data/[owner_repo]/code/`
- Generate gists to `data/[owner_repo]/gist/[repo]_gist.txt`
- Track state in `data/crawl-state.json`

### 3. Purge Data

```bash
make purge
```

Removes all crawled data and state files.

## Directory Structure

```
gist-crawl/
├── .gitignore                    # Git ignore rules
├── crawl-jobs.txt                # Queue of repositories to crawl
├── data/                         # Crawl output directory
│   ├── crawl-state.json          # Crawl history and state tracking
│   └── [owner_repo]/             # Per-repository directory
│       ├── code/                 # Git clone of repository
│       └── gist/                 # Generated gist files
│           └── [repo]_gist.txt   # Repository gist
├── gist-crawler.py               # Main crawler script
├── Makefile                      # Build automation
├── pyproject.toml                # Python dependencies
├── README.md                     # This file
└── uv.lock                       # Dependency lock file
```

## Make Targets

### `make help`

Shows available make targets (default target).

```bash
make help
```

### `make init`

Installs dependencies and creates the data directory.

```bash
make init
```

### `make crawl`

Runs the crawler on repositories listed in `crawl-jobs.txt`. Automatically runs `make init` if needed.

```bash
make crawl
```

### `make purge`

Removes all crawled data, state files, and temporary downloads.

```bash
make purge
```

## How It Works

### Smart Update Behavior

1. **First Run**: Clones repository and generates gist
2. **Subsequent Runs**:
   - Runs `git pull` to check for updates
   - If commit SHA changed: Regenerates gist
   - If no changes: Skips gist generation
3. **Missing Gist**: Regenerates even if repository unchanged

This minimizes unnecessary gitingest.com requests and processing time.

### Gist Generation

The crawler uses [gitingest.com](https://gitingest.com/) via Selenium to generate comprehensive repository gists containing:
- Repository structure
- File contents
- Metadata

These gists are ideal for:
- LLM context ingestion
- Code analysis
- Documentation generation
- Repository summaries

## Example Workflow

```bash
# First time setup
make init

# Add repositories to crawl-jobs.txt
echo "https://github.com/coderamp-labs/gitingest" >> crawl-jobs.txt

# Run crawler
make crawl

# View generated gist
cat data/coderamp-labs_gitingest/gist/gitingest_gist.txt

# Clean up everything
make purge
```

## State Tracking

The `data/crawl-state.json` file tracks processing history:

```json
{
  "https://github.com/owner/repo": {
    "last_crawled": "2024-01-15 10:30:00",
    "repo_identifier": "owner_repo",
    "gist_path": "data/owner_repo/gist/repo_gist.txt",
    "status": "success"
  }
}
```

## Troubleshooting

### Chrome Not Found

Ensure Google Chrome is installed. Selenium will automatically download and manage the ChromeDriver.

### Git Authentication

For private repositories, configure Git credentials:

```bash
git config --global credential.helper store
```

### gitingest.com Timeout

Large repositories may timeout. Default timeout is 60 seconds for processing. Modify `generate_digest()` timeout in `gist-crawler.py` if needed.

## Limitations

This project uses Selenium to automate the [gitingest.com](https://gitingest.com/) website for gist generation. This approach has limitations:

- **Fragile**: Gist generation will break if the website UI changes
- **Slower**: Browser automation adds overhead compared to direct API calls
- **Less Robust**: No native error handling or rate limiting

### Recommended Alternative

For a more robust implementation, use the [gitingest Python library](https://github.com/coderamp-labs/gitingest) directly with proper GitHub API authentication. This would provide:
- Direct API access without browser automation
- Better error handling and rate limiting
- No dependency on website UI stability
- Faster processing
