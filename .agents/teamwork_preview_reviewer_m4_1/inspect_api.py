import inspect
import importlib

modules = [
    "morphomesh.assembler.__init__",
    "morphomesh.assembler.scene_builder",
    "morphomesh.assembler.pbr_baker",
    "morphomesh.assembler.packager",
    "morphomesh.assembler.assembler",
    "morphomesh.character_assembler",
]

for mod_name in modules:
    print(f"\n==================== {mod_name} ====================")
    mod = importlib.import_module(mod_name)
    mod_doc = inspect.getdoc(mod)
    print(f"Module docstring: {'YES' if mod_doc else 'NO'}")
    
    # Check all members defined in this module
    for name, obj in inspect.getmembers(mod):
        if name.startswith("__"):
            continue
        # Only inspect objects defined in this module (or exported classes/functions)
        if inspect.isfunction(obj) or inspect.isclass(obj):
            obj_mod = getattr(obj, "__module__", "")
            # If function/class belongs to this module
            if obj_mod == mod_name:
                doc = inspect.getdoc(obj)
                sig = None
                try:
                    sig = inspect.signature(obj)
                except Exception:
                    pass
                print(f"  {type(obj).__name__} {name}{sig}: Docstring={'YES' if doc else 'NO'}")
                if inspect.isclass(obj):
                    for m_name, m_obj in inspect.getmembers(obj, predicate=inspect.isfunction):
                        if not m_name.startswith("_") or m_name in ("__init__", "to_dict"):
                            m_doc = inspect.getdoc(m_obj)
                            try:
                                m_sig = inspect.signature(m_obj)
                            except Exception:
                                m_sig = ""
                            print(f"    method {m_name}{m_sig}: Docstring={'YES' if m_doc else 'NO'}")
