# Deepwick for eza

Deepwick colors for [eza](https://eza.rocks).

> Deepwick is an unofficial theme derived from
> [Polywick Blue](https://vscode.polywickstudio.net) by Polywick Studio (MIT).
> Not affiliated with Polywick Studio.

![Deepwick in eza](screenshot.png)

## Install

```sh
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/eza"
cp deepwick.yml "${XDG_CONFIG_HOME:-$HOME/.config}/eza/theme.yml"
```

If you set `EZA_CONFIG_DIR`, copy it to `$EZA_CONFIG_DIR/theme.yml` instead;
eza then ignores `~/.config/eza`.

## Notes

- **`LS_COLORS` and `EZA_COLORS` win over `theme.yml`.** Many distributions
  export `LS_COLORS`, so file names keep those colors. Either install
  [Deepwick for dircolors](https://github.com/deepwick/dircolors) so both
  agree, or run eza without it: `alias eza='env -u LS_COLORS eza'`.
- eza ignores the whole file if any value is malformed and falls back to its
  defaults without an error.
- Broken symlinks keep the symlink color on their name; the arrow and the
  missing target are Red.
- Git column: new/untracked Teal, modified Blue, deleted Red, ignored Muted.
  Permissions: read Yellow, write Red, execute Green. Sizes Sage, users Light
  Blue, groups and dates Comment.
- Pass a path (`eza .`) in scripts and pipelines: eza 0.23.5 prints nothing
  when run without one and its stdin isn't a terminal.

Tested with eza 0.23.5.

## License

MIT. See [LICENSE](LICENSE).
