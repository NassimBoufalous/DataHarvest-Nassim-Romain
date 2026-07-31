# DataHarvest

Mini-framework de web scraping modulaire et configurable développé dans le cadre du projet final de Web Scraping du Mastère Développement, Data & IA (IPSSI Montpellier).

Le projet permet de scraper différents sites HTML statiques **sans modifier le code Python** : toute la configuration du scraping (URL, pagination, sélecteurs CSS, validation, stockage...) est définie dans un simple fichier YAML ou JSON.

---

## Équipe

* **Nassim Boufalous**
* **Romain Pintre**

Formation : Mastère Développement, Data & IA (4ᵉ année) – IPSSI Montpellier

Date : Juillet 2026

---

# Objectifs

DataHarvest a été conçu comme un mini-framework réutilisable plutôt qu'un scraper dédié à un seul site.

L'objectif est de proposer une architecture modulaire où chaque composant possède une responsabilité unique :

* chargement de configuration ;
* téléchargement HTTP ;
* extraction des données ;
* validation des éléments ;
* stockage multi-backend ;
* orchestration complète via une interface en ligne de commande.

Le changement de site à scraper ne nécessite qu'un changement de fichier de configuration.

---

# Architecture

```
                    +-----------------+
                    |     Config      |
                    |   YAML / JSON   |
                    +--------+--------+
                             |
                             v
                    +-----------------+
                    |  Orchestrator   |
                    +--------+--------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
  +-----------+       +-------------+      +-------------+
  |  Fetcher  | ----> |  Pipeline   | ---> | Validator   |
  | +Middleware| HTML | Extraction  |items | Validation  |
  +-----------+       +-------------+      +------+------+ 
                                                   |
                                                   v
                                            +-------------+
                                            |    Store    |
                                            | csv/json/db |
                                            +-------------+
```

Le projet repose sur une **injection de dépendances** : chaque composant reçoit ses dépendances via son constructeur plutôt que par import direct.

Exemple :

```python
Fetcher(config, middlewares=[...])
```

Cette approche facilite :

* les tests unitaires ;
* le remplacement d'un composant ;
* l'évolution du framework.

---

# Composants

## Config

Responsable du chargement des fichiers YAML/JSON.

Fonctionnalités :

* validation des champs obligatoires ;
* erreurs explicites ;
* accès aux paramètres via des attributs (`config.fetcher.delay`).

---

## Middleware

Gestion des traitements transverses appliqués aux requêtes HTTP.

Middlewares disponibles :

* LoggingMiddleware
* RetryMiddleware

Le projet est conçu pour pouvoir accueillir facilement un futur `RateLimitMiddleware`.

---

## Fetcher

Téléchargement HTTP via `requests.Session`.

Fonctionnalités :

* timeout ;
* retries ;
* chaîne de middlewares ;
* levée d'une exception personnalisée (`FetchError`) en cas d'échec.

---

## Pipeline

Extraction générique des données grâce aux sélecteurs CSS.

Deux implémentations :

* GenericPipeline
* PaginationPipeline

Fonctionnalités :

* extraction texte ;
* extraction d'attributs (`title`, `datetime`, etc.) ;
* conversion automatique des URLs relatives ;
* pagination configurable ;
* arrêt automatique lorsqu'il n'y a plus d'éléments.

---

## Validator

Filtre les éléments invalides :

* champs obligatoires ;
* URLs valides ;
* longueur minimale configurable.

Les éléments rejetés sont journalisés avec leur motif.

---

## Store

Persistance des données dans plusieurs formats :

* CSV
* JSON
* SQLite

Fonctionnalités :

* déduplication par URL ;
* export d'un backend vers un autre ;
* création dynamique du schéma SQLite selon les champs rencontrés.

---

## Orchestrator

Chef d'orchestre du framework.

Il pilote le cycle complet :

```
Config
   ↓
Fetcher
   ↓
Pipeline
   ↓
Validator
   ↓
Store
```

À la fin du traitement, il retourne un rapport contenant :

* pages parcourues ;
* éléments extraits ;
* éléments valides ;
* éléments rejetés ;
* éléments stockés ;
* durée totale.

---

## CLI

Le projet expose trois commandes :

* crawl
* validate
* export

---

# Installation

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

---

# Utilisation

## Lancer un scraping

```bash
python -m dataharvest crawl --config configs/site1.yaml
```

### Mode Dry Run

Télécharge uniquement la première page, affiche les résultats sans les enregistrer.

```bash
python -m dataharvest crawl --config configs/site1.yaml --dry-run
```

### Vérifier une configuration

```bash
python -m dataharvest validate --config configs/site1.yaml
```

### Exporter un backend

```bash
python -m dataharvest export --from output/books.db --to output/books.csv
```

---

# Sites scrappés

| Site                 | Difficulté | Backend | Résultat                                |
| -------------------- | ---------- | ------- | --------------------------------------- |
| books.toscrape.com   | ★          | SQLite  | 60 éléments                             |
| quotes.toscrape.com  | ★          | CSV     | 30 éléments                             |
| pypi.org/search      | ★★         | JSON    | Échec documenté (anti-bot + robots.txt) |
| blogdumoderateur.com | ★★★        | SQLite  | 36 éléments                             |
| news.ycombinator.com | ★★★★       | CSV     | 90 éléments                             |

Le projet couvre ainsi **quatre niveaux de difficulté différents**, conformément au sujet.

---

# Tests

Le projet comporte :

* **44 tests unitaires**
* **1 test d'intégration**

Couverture globale :

**89 %**

Exécution :

```bash
pytest --cov=dataharvest --cov-report=term-missing -v
```

Tests unitaires uniquement :

```bash
pytest -m "not integration"
```

---

# Choix de conception

Les principaux choix techniques sont :

* architecture orientée composants ;
* injection de dépendances ;
* utilisation d'ABC (`BasePipeline`, `BaseMiddleware`) ;
* middleware pour découpler le téléchargement HTTP des politiques de retry et de logging ;
* configuration externe via YAML plutôt que des dizaines d'arguments CLI.

Cette architecture facilite les tests et permet de remplacer facilement un composant sans modifier les autres.

---

# Limites connues

Le framework présente volontairement certaines limites :

* uniquement des sites HTML statiques ;
* pas de rendu JavaScript ;
* pagination basée sur un pattern d'URL ;
* extraction positionnelle pouvant être perturbée par des champs optionnels absents.

Le cas de **PyPI** est volontairement conservé comme exemple d'échec réel : le site applique désormais une protection anti-bot et interdit également `/search` dans son `robots.txt`.

---

# Éthique

Le projet respecte les bonnes pratiques du scraping :

* User-Agent identifiable ;
* délai entre les requêtes ;
* retries avec backoff exponentiel ;
* déduplication des données ;
* prise en compte des fichiers `robots.txt`.

Les données collectées proviennent uniquement de pages publiques et le projet est réalisé dans un cadre pédagogique.

---

# Perspectives

Plusieurs évolutions sont envisageables :

* ajout d'un `RateLimitMiddleware` ;
* prise en charge de Playwright pour les sites JavaScript ;
* système de notification (Discord, Slack, e-mail) lorsque le scraping extrait trop peu de données ;
* publication du framework sur PyPI ;
* intégration continue via GitHub Actions.

---

# Répartition du travail

### Nassim Boufalous

* Middleware
* Fetcher
* Validator
* CLI
* Tests associés

### Romain Pintre

* Config
* Pipeline
* Store
* Orchestrator
* Configurations des cinq sites
* Grande majorité des tests unitaires
* Test d'intégration

Les développements ont été intégrés progressivement via Git, avec plusieurs corrections apportées lors de l'assemblage des composants.

---

# Technologies utilisées

* Python 3
* Requests
* BeautifulSoup4
* lxml
* SQLite
* CSV
* JSON
* PyYAML
* pytest

---

# Licence

Projet pédagogique réalisé dans le cadre du Mastère Développement, Data & IA de l'IPSSI Montpellier.
