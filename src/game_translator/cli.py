from __future__ import annotations

import argparse
import json

from .services import (
    import_runtime_service,
    inspect_game_service,
    inspect_runtime_service,
    install_service,
    uninstall_service,
)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "inspect-game":
        print(json.dumps(inspect_game_service(args.game), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "import-runtime":
        print(
            json.dumps(
                import_runtime_service(args.source_game, args.runtime_root),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "inspect-runtime":
        print(json.dumps(inspect_runtime_service(args.runtime_root), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "install":
        print(
            json.dumps(
                install_service(
                    args.game,
                    args.runtime_root,
                    args.target_language,
                    dry_run=args.dry_run,
                ),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    if args.command == "uninstall":
        print(json.dumps(uninstall_service(args.game), ensure_ascii=False, indent=2, default=str))
        return

    parser.error("未知命令")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="私人游戏翻译器")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_game = subparsers.add_parser("inspect-game", help="检查游戏目录")
    inspect_game.add_argument("game")

    import_runtime = subparsers.add_parser("import-runtime", help="从已汉化游戏导入运行时")
    import_runtime.add_argument("--source-game", required=True)
    import_runtime.add_argument("--runtime-root", required=True)

    inspect_runtime = subparsers.add_parser("inspect-runtime", help="检查运行时目录")
    inspect_runtime.add_argument("--runtime-root", required=True)

    install = subparsers.add_parser("install", help="安装翻译运行时")
    install.add_argument("--game", required=True)
    install.add_argument("--runtime-root", required=True)
    install.add_argument("--target-language", default="zh")
    install.add_argument("--dry-run", action="store_true")

    uninstall = subparsers.add_parser("uninstall", help="回滚安装")
    uninstall.add_argument("--game", required=True)

    return parser


if __name__ == "__main__":
    main()
