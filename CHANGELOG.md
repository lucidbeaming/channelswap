# Changelog

All notable changes to this project are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] - 2026-11-23

First release. `--bright` works (it failed on every image), Pillow 9.1+ is required, and the README has before/after examples.

### Added
- README: before/after example images, input/output naming, related projects (#5)

### Fixed
- `--bright` works: it called a nonexistent `_enhance()` and discarded the adjusted sections (#7)
- Pillow floor raised to 9.1, which added the `Image.Resampling` API `swap.py` uses (#5)

### Changed
- Relicensed from GPL-3.0 to MIT; earlier releases keep GPL-3.0 (#1)
- `.gitignore`: macOS/editor files, env files, and the `input/` and `output/` example folders (#3)

[Unreleased]: https://github.com/lucidbeaming/channelswap/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/lucidbeaming/channelswap/releases/tag/v1.0.0
