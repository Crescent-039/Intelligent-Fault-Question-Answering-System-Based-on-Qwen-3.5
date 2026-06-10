from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from Communication import RagChatService


def main():
    project_root = PROJECT_ROOT
    preferred_path = project_root / "midway" / "upload" / "tmp"
    fallback_path = project_root / "docs"
    path = preferred_path if preferred_path.exists() else fallback_path

    print(f"索引路径: {path}")
    service = RagChatService()
    service.init_rag_service(load_llm=False, warmup=False)
    result = service.add_path_to_index(str(path))
    print(result)


if __name__ == "__main__":
    main()
