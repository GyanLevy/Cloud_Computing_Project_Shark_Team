"""
Generate the complete Colab notebook for the My Garden Care project.
Run this script to create a properly formatted .ipynb file.
"""
import json
import os

def create_notebook():
    cells = []
    
    # Header cell
    cells.append({
        "cell_type": "markdown",
        "source": [
            "# 🌿 My Garden Care - Cloud Computing Project\n",
            "\n",
            "**Team: Shark Team**\n",
            "\n",
            "---\n",
            "\n",
            "## Instructions:\n",
            "1. **Run Cell 1** to install all dependencies\n",
            "2. **Upload** `serviceAccountKey.json` to the Colab file browser\n",
            "3. **Run Cell 2** to set your Google API key\n",
            "4. **Run all %%writefile cells** to create project files\n",
            "5. **Create `articles_data/` folder** and upload knowledge base files\n",
            "6. **Run the final cell** to launch the application"
        ],
        "metadata": {}
    })
    
    # Cell 1: Install dependencies
    cells.append({
        "cell_type": "markdown",
        "source": ["## 📦 Cell 1: Install Dependencies"],
        "metadata": {}
    })
    cells.append({
        "cell_type": "code",
        "source": ["!pip install -q firebase-admin nltk google-cloud-firestore google-auth numpy gradio matplotlib requests python-docx scikit-learn sentence-transformers chromadb google-generativeai python-dotenv"],
        "metadata": {},
        "execution_count": None,
        "outputs": []
    })
    
    # Cell 2: API Keys
    cells.append({
        "cell_type": "markdown",
        "source": ["## 🔑 Cell 2: Security Setup (Colab Secrets)\n\n**Before running this cell, add these secrets:**\n\n1. Click the **🔑 Key icon** (Secrets) in the left sidebar\n2. Add **two secrets**:\n\n| Secret Name | Value |\n|-------------|-------|\n| `GOOGLE_API_KEY` | Your Gemini API key |\n| `FIREBASE_JSON` | Copy & paste the **entire content** of your `serviceAccountKey.json` file |\n\n3. Toggle the switch to enable notebook access for both secrets"],
        "metadata": {}
    })
    cells.append({
        "cell_type": "code",
        "source": [
            "import os\n",
            "from google.colab import userdata\n",
            "\n",
            "# 1. Setup Gemini API Key\n",
            "try:\n",
            "    os.environ['GOOGLE_API_KEY'] = userdata.get('GOOGLE_API_KEY')\n",
            "    print('✅ Gemini API Key loaded from Secrets.')\n",
            "except Exception:\n",
            "    print('❌ Error: GOOGLE_API_KEY secret is missing.')\n",
            "    print('   Add it in the 🔑 Secrets panel on the left sidebar.')\n",
            "\n",
            "# 2. Setup Firebase Credentials\n",
            "try:\n",
            "    # User pastes the content of serviceAccountKey.json into this secret\n",
            "    firebase_json_content = userdata.get('FIREBASE_JSON')\n",
            "    \n",
            "    # Write it to a file so the app can use it normally\n",
            "    with open('serviceAccountKey.json', 'w') as f:\n",
            "        f.write(firebase_json_content)\n",
            "    \n",
            "    os.environ['FIREBASE_CREDENTIALS_PATH'] = '/content/serviceAccountKey.json'\n",
            "    print('✅ Firebase credentials created from Secrets.')\n",
            "except Exception:\n",
            "    print('❌ Error: FIREBASE_JSON secret is missing.')\n",
            "    print('   Copy the entire content of your serviceAccountKey.json file')\n",
            "    print('   and paste it into a secret named FIREBASE_JSON.')"
        ],
        "metadata": {},
        "execution_count": None,
        "outputs": []
    })
    
    # Create UI directory
    cells.append({
        "cell_type": "markdown",
        "source": ["## 📁 Cell 3: Create Project Structure"],
        "metadata": {}
    })
    cells.append({
        "cell_type": "code",
        "source": [
            "import os\n",
            "os.makedirs('ui', exist_ok=True)\n",
            "os.makedirs('articles_data', exist_ok=True)\n",
            "print('✅ Directories created: ui/, articles_data/')"
        ],
        "metadata": {},
        "execution_count": None,
        "outputs": []
    })
    
    # Read all Python files and create cells for each
    files_to_include = [
        ("config.py", "config.py"),
        ("gamification_rules.py", "gamification_rules.py"),
        ("auth_service.py", "auth_service.py"),
        ("plants_manager.py", "plants_manager.py"),
        ("data_manager.py", "data_manager.py"),
        ("logic_handler.py", "logic_handler.py"),
        ("main.py", "main.py"),
        ("app.py", "app.py"),
        ("ui/__init__.py", "ui/__init__.py"),
        ("ui/auth_ui.py", "ui/auth_ui.py"),
        ("ui/home_ui.py", "ui/home_ui.py"),
        ("ui/plants_ui.py", "ui/plants_ui.py"),
        ("ui/sensors_ui.py", "ui/sensors_ui.py"),
        ("ui/dashboard_ui.py", "ui/dashboard_ui.py"),
        ("ui/search_ui.py", "ui/search_ui.py"),
        ("ui/upload_ui.py", "ui/upload_ui.py"),
    ]
    
    cell_num = 4
    for filepath, writefile_path in files_to_include:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fix escaped quotes issue from previous edits
            content = content.replace('\\"\\"\\"', '"""')
            
            cells.append({
                "cell_type": "markdown",
                "source": [f"### Cell {cell_num}: {filepath}"],
                "metadata": {}
            })
            cells.append({
                "cell_type": "code",
                "source": [f"%%writefile {writefile_path}\n{content}"],
                "metadata": {},
                "execution_count": None,
                "outputs": []
            })
            cell_num += 1
            print(f"✅ Added {filepath}")
        else:
            print(f"⚠️ File not found: {filepath}")
    
    # Final run cell
    cells.append({
        "cell_type": "markdown",
        "source": ["---\n## 🚀 Final Cell: Launch Application"],
        "metadata": {}
    })
    cells.append({
        "cell_type": "code",
        "source": [
            "# Run the application with public sharing enabled\n",
            "!python app.py"
        ],
        "metadata": {},
        "execution_count": None,
        "outputs": []
    })
    
    # Create notebook structure
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {
                "provenance": []
            },
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "cells": cells
    }
    
    # Write notebook
    output_path = "MyGardenCare_Colab_Notebook.ipynb"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(notebook, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Notebook created: {output_path}")
    print(f"   Total cells: {len(cells)}")
    return output_path

if __name__ == "__main__":
    create_notebook()
