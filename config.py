from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1] 

SOURCE = {
    "SDK": {
        "namespace": "wandb",
        "pckg_init_file": {
            "__init__.py": BASE_DIR / "wandb" / "wandb" / "__init__.py",
            "__init__.pyi": BASE_DIR / "wandb" / "wandb" / "__init__.pyi",
        }
    },
    "PUBLIC": {
        "namespace": "wandb.apis.public",
        "pckg_init_file": {
            "__init__.py": BASE_DIR / "wandb" / "wandb" / "apis" / "public" / "__init__.py",
            "__init__.pyi": None
        }
    },
    "AUTOMATIONS": {
        "namespace": "wandb.automations",
        "pckg_init_file": {
            "__init__.py": BASE_DIR / "wandb" / "wandb" / "automations" / "__init__.py",
            "__init__.pyi": None
        }      
    },
    "CUSTOMCHARTS": {
        "namespace": "wandb.plot",
        "pckg_init_file": {
            "__init__.py": BASE_DIR / "wandb" / "wandb" / "plot" / "__init__.py",
            "__init__.pyi": None
        },
    },      
}