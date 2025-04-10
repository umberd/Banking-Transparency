"""
Direct script to compile translation files (.po to .mo)
"""
import os
import sys

try:
    print("Starting translation compilation...")
    
    # List all language directories
    translations_dir = "translations"
    print(f"Checking translations directory: {os.path.abspath(translations_dir)}")
    
    lang_dirs = [d for d in os.listdir(translations_dir) if os.path.isdir(os.path.join(translations_dir, d))]
    print(f"Found language directories: {lang_dirs}")
    
    for lang in lang_dirs:
        # Path to the .po file
        po_path = os.path.join(translations_dir, lang, "LC_MESSAGES", "messages.po")
        # Path for the .mo file to be created
        mo_path = os.path.join(translations_dir, lang, "LC_MESSAGES", "messages.mo")
        
        if not os.path.exists(po_path):
            print(f"Warning: .po file not found at {po_path}")
            continue
        
        print(f"Compiling {lang} translations: {po_path} -> {mo_path}")
        
        # Import babel modules inside the function to get clear errors if they're not found
        try:
            from babel.messages.pofile import read_po
            from babel.messages.mofile import write_mo
            
            with open(po_path, 'rb') as po_file:
                catalog = read_po(po_file)
            
            with open(mo_path, 'wb') as mo_file:
                write_mo(mo_file, catalog)
            
            print(f"Successfully compiled {lang} translations")
            
        except ImportError as e:
            print(f"Error importing Babel modules: {e}")
            print("Make sure Babel is installed: pip install babel")
            sys.exit(1)
        except Exception as e:
            print(f"Error compiling {lang} translations: {e}")
            import traceback
            traceback.print_exc()
    
    print("\nAll translations compiled successfully!")
    
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
