import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

class DataLoader:
    def __init__(self, host, user, password, index_id):
        self.es = Elasticsearch(host, basic_auth=(user, password))
        self.index_id = index_id
        self.core_cols = ["ticket", "tache_objet", "statut_tache", "priorite", "date_debut", "date_finprevue", "date_fin", "proces_label", "proces_statut", "site_nom", "site_statut", "zone", "region", "departement", "projet_nom", "annee", "porteur", "equipe", "domaine", "utilisateur", "statut_global"]

    def fetch_and_process(self):
        results = scan(self.es, index=self.index_id, query={"query": {"match_all": {}}})
        df = pd.DataFrame([doc['_source'] for doc in results])
        if df.empty:
            return []
        df = df.drop_duplicates("ticket")

        # 1. Gestion et nettoyage de la date de début (Clé pour "le dernier ticket")
        if "date_debut" in df.columns:
            # On convertit en format datetime pour pouvoir manipuler la chronologie si besoin
            df["date_debut_clean"] = pd.to_datetime(df["date_debut"], errors='coerce')
            # On crée une colonne textuelle propre pour l'affichage
            df["date_debut_str"] = df["date_debut_clean"].dt.strftime('%d/%m/%Y à %H:%M').fillna("non renseignée")
        else:
            df["date_debut_str"] = "non renseignée"

        # Nettoyage et Stats des colonnes textuelles
        clean_cols = ["tache_objet", "proces_label", "site_nom", "zone", "region", 
                      "departement", "projet_nom", "porteur", "utilisateur", "annee", "priorite", "statut_tache"]
        
        for col in clean_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.lower().str.strip()

        # Calcul des stats globales par catégorie
        stats_mapping = {'zone': 'total_tasks_zone','projet_nom': 'total_tasks_projet','region': 'total_tasks_region','departement': 'total_tasks_departement','porteur': 'total_tasks_porteur','utilisateur': 'total_tasks_utilisateur','domaine': 'total_tasks_domaine','proces_label': 'total_tasks_process_label','annee': 'total_tasks_annee','statut_tache': 'total_tasks_statut_tache','priorite': 'total_tasks_priorite'}
        for col_orig, col_dest in stats_mapping.items():
            if col_orig in df.columns:
                df[col_dest] = df.groupby(col_orig)['ticket'].transform('count')
        
        # 2. NOUVEAU : Calculs croisés avec le Statut de la tâche
        if 'region' in df.columns and 'statut_tache' in df.columns:
           df['tasks_region_by_status'] = df.groupby(['region', 'statut_tache'])['ticket'].transform('count')

        if 'zone' in df.columns and 'statut_tache' in df.columns:
           df['tasks_zone_by_status'] = df.groupby(['zone', 'statut_tache'])['ticket'].transform('count')
        
        # 3. NOUVEAU : Calculs croisés avec la priorité de la tâche 
        if 'region' in df.columns and 'priorite' in df.columns:
           df['tasks_region_by_priority'] = df.groupby(['region', 'priorite'])['ticket'].transform('count')
        
        if 'zone' in df.columns and 'priorite' in df.columns:
              df['tasks_zone_by_priority'] = df.groupby(['zone', 'priorite'])['ticket'].transform('count')

        # 4. NOUVEAU : Calculs croisés avec le porteur de la tâche
        if 'region' in df.columns and 'porteur' in df.columns:
           df['tasks_region_by_porteur'] = df.groupby(['region', 'porteur'])['ticket'].transform('count')
        
        if 'zone' in df.columns and 'porteur' in df.columns:
             df['tasks_zone_by_porteur'] = df.groupby(['zone', 'porteur'])['ticket'].transform('count')
        
        # 5. NOUVEAU : calculs croisés avec l'utilisateur de la tâche
        if 'region' in df.columns and 'utilisateur' in df.columns:
           df['tasks_region_by_utilisateur'] = df.groupby(['region', 'utilisateur'])['ticket'].transform('count')
        
        if 'zone' in df.columns and 'utilisateur' in df.columns:
           df['tasks_zone_by_utilisateur'] = df.groupby(['zone', 'utilisateur'])['ticket'].transform('count')
        
        if 'projet_nom' in df.columns and 'statut_tache' in df.columns:
           df['tasks_projet_by_status'] = df.groupby(['projet_nom', 'statut_tache'])['ticket'].transform('count')
        
        if 'projet_nom' in df.columns and 'priorite' in df.columns:
           df['tasks_projet_by_priority'] = df.groupby(['projet_nom', 'priorite'])['ticket'].transform('count')
        
        if 'projet_nom' in df.columns and 'annee' in df.columns:
           df['tasks_projet_by_annee'] = df.groupby(['projet_nom', 'annee'])['ticket'].transform('count')

        # Construction du texte source
        df["document_text"] = df.apply(self._build_full_source_text, axis=1)
        
        return df[["document_text", "ticket"]].to_dict(orient="records")

    def _build_full_source_text(self, row):
        region = row.get('region', 'inconnue')
        zone = row.get('zone', 'inconnue')
        departement = row.get('departement', 'inconnu')
        statut = row.get('statut_tache', 'inconnu')
        priorite = row.get('priorite', 'inconnue')
        porteur = row.get('porteur', 'inconnu')
        utilisateur = row.get('utilisateur', 'inconnu')
        
        # Reconstruction intelligente de la section STATS (Croisements multidimensionnels)
        stat_parts = [
            f"Statistiques globales et croisements de référence :",
            f"- Pour le projet '{row.get('projet_nom')}', il y a {row.get('total_tasks_projet', 0)} tâches au total.",
            f"- [PROJET + CRITÈRES] : {row.get('tasks_projet_by_status', 0)} tâches sont '{statut}', {row.get('tasks_projet_by_priority', 0)} sont en priorité '{priorite}' et {row.get('tasks_projet_by_annee', 0)} datent de {row.get('annee')}.",
            f"- [GÉOGRAPHIE - RÉGION] : La région '{region}' compte {row.get('total_tasks_region', 0)} tâches globales.",
            f"  -> Croisements Région : {row.get('tasks_region_by_status', 0)} au statut '{statut}', {row.get('tasks_region_by_priority', 0)} de priorité '{priorite}', {row.get('tasks_region_by_porteur', 0)} affectées à {porteur}.",
            f"- [GÉOGRAPHIE - ZONE] : La zone '{zone}' ({region}) compte {row.get('total_tasks_zone', 0)} tâches.",
            f"  -> Croisements Zone : {row.get('tasks_zone_by_status', 0)} au statut '{statut}', {row.get('tasks_zone_by_priority', 0)} de priorité '{priorite}', {row.get('tasks_zone_by_porteur', 0)} affectées à {porteur}.",
            f"- Le statut général '{statut}' concerne actuellement {row.get('total_tasks_statut_tache', 0)} tickets dans l'application.",
            f"- Porteurs & Assignations : {porteur} gère {row.get('total_tasks_porteur', 0)} tâches et {utilisateur} en gère {row.get('total_tasks_utilisateur', 0)}."
        ]
        stat_context = "\n".join(stat_parts)
        
        # Section DETAILS : Injection claire de la date de début calculée pour le LLM
        detail_parts = [
            f"Détails spécifiques du ticket n°{row['ticket']} :",
            f"- Le ticket a été initié/ouvert le : '{row.get('date_debut_str')}'"
        ]
        
        for col in self.core_cols:
            if col in ["ticket", "projet_nom", "zone", "date_debut"]:
                continue
            
            value = row.get(col, None)
            if pd.notnull(value) and str(value).lower() not in ["none", "nan", "null"]:
                detail_parts.append(f"- Le champ {col} a pour valeur : '{value}'")
        detail_parts_str = "\n".join(detail_parts)
        
        return f"[STATS]:\n{stat_context}\n\n[DETAILS]:\n{detail_parts_str}"