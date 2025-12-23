# 🌿 My Garden Care - Project Architecture

## System Overview

This document provides a comprehensive architecture diagram of the **My Garden Care** cloud-based plant management system.

---

## Architecture Diagram

```mermaid
graph TD
    subgraph User["👤 User"]
        Browser["Web Browser"]
    end

    subgraph Presentation["🎨 Presentation Layer (Gradio UI)"]
        main["main.py<br/>Entry Point"]
        home_ui["home_ui.py<br/>Main App Shell"]

        subgraph UI_Screens["UI Screens"]
            auth_ui["auth_ui.py<br/>Login/Register"]
            plants_ui["plants_ui.py<br/>My Plants Gallery"]
            sensors_ui["sensors_ui.py<br/>IoT Sensors"]
            dashboard_ui["dashboard_ui.py<br/>Plant Dashboard"]
            upload_ui["upload_ui.py<br/>Upload Photos"]
            search_ui["search_ui.py<br/>RAG Search"]
        end
    end

    subgraph Logic["⚙️ Logic/Service Layer"]
        auth_service["auth_service.py<br/>• register_user<br/>• login_user<br/>• update_score<br/>• leaderboard"]
        plants_manager["plants_manager.py<br/>• add_plant<br/>• list_plants<br/>• delete_plant<br/>• upload_image"]
        data_manager["data_manager.py<br/>• IoT sync<br/>• Sensor history<br/>• Articles CRUD<br/>• RAG/Vector Search"]
        gamification["gamification_rules.py<br/>• Points system<br/>• Weekly challenges<br/>• User ranks"]
    end

    subgraph Data["💾 Data Access Layer"]
        config["config.py<br/>• Firebase init<br/>• Singleton DB client<br/>• Storage bucket"]
    end

    subgraph External["☁️ External Infrastructure"]
        subgraph Firebase["Firebase Platform"]
            Firestore["Firestore DB<br/>• users/{username}<br/>• users/{}/plants/{}<br/>• sensors<br/>• articles<br/>• index"]
            Storage["Cloud Storage<br/>• user_uploads/{user}/*.png"]
        end

        IoT_Server["External IoT Server<br/>render.com<br/>/history endpoint"]
    end

    %% User Flow
    Browser --> main
    main --> home_ui
    home_ui --> UI_Screens

    %% UI to Logic connections
    auth_ui --> auth_service
    plants_ui --> plants_manager
    sensors_ui --> data_manager
    dashboard_ui --> data_manager
    dashboard_ui --> plants_manager
    upload_ui --> plants_manager
    search_ui --> data_manager

    %% Logic interdependencies
    auth_service --> gamification
    auth_service --> config
    plants_manager --> config
    data_manager --> config

    %% Data Layer to Firebase
    config --> Firestore
    config --> Storage
    plants_manager --> Storage
    data_manager --> IoT_Server
```

---

## Layer Breakdown

### 🎨 Presentation Layer

| File              | Purpose                                                 |
| ----------------- | ------------------------------------------------------- |
| `main.py`         | Application entry point, initializes DB and launches UI |
| `home_ui.py`      | Main shell with navigation, logout, metrics overview    |
| `auth_ui.py`      | Login/Register forms                                    |
| `plants_ui.py`    | Gallery view of user's plants                           |
| `sensors_ui.py`   | IoT sensor data display                                 |
| `dashboard_ui.py` | Plant health dashboard with charts                      |
| `upload_ui.py`    | Photo upload interface                                  |
| `search_ui.py`    | RAG-powered knowledge base search                       |

### ⚙️ Logic/Service Layer

| File                    | Purpose                                                     |
| ----------------------- | ----------------------------------------------------------- |
| `auth_service.py`       | User authentication, password hashing, gamification scoring |
| `plants_manager.py`     | Plant CRUD operations, image upload to Cloud Storage        |
| `data_manager.py`       | IoT data sync, sensor history, articles, RAG vector search  |
| `gamification_rules.py` | Points definitions, weekly challenges, user ranks           |

### 💾 Data Access Layer

| File        | Purpose                                                               |
| ----------- | --------------------------------------------------------------------- |
| `config.py` | Firebase initialization (singleton), Firestore client, Storage bucket |

### ☁️ External Infrastructure

| Service           | Purpose                                                |
| ----------------- | ------------------------------------------------------ |
| **Firestore**     | Document database for users, plants, sensors, articles |
| **Cloud Storage** | Image storage for plant photos                         |
| **IoT Server**    | External sensor data source (Render.com)               |

---

## Data Flow Examples

### 1️⃣ User Registration

```
Browser → auth_ui.py → auth_service.register_user() → config.get_db() → Firestore (users collection)
```

### 2️⃣ Upload Plant Photo

```
Browser → upload_ui.py → plants_manager.add_plant_with_image() → Cloud Storage → Firestore (plants subcollection)
```

### 3️⃣ View Sensor Data

```
Browser → sensors_ui.py → data_manager.sync_iot_data() → IoT Server API → Firestore → sensors_ui.py → Browser
```

### 4️⃣ RAG Search

```
Browser → search_ui.py → data_manager.PlantRAG.query() → Vector Store + Articles → LLM/Template → Browser
```

---

## Firestore Data Model

```
📁 users/{username}
    ├── display_name, email, password (hashed)
    ├── score, tasks_completed
    ├── challenge_state
    └── 📁 plants/{plant_id}
            └── name, species, image_url, created_at

📁 sensors/{doc_id}
    └── plant_id, temp, humidity, soil, timestamp

📁 articles/{doc_id}
    └── title, content, url, metadata

📁 index/{term}
    └── doc_ids[], term
```
