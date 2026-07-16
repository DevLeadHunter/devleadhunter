# credentials/

Dossier des clés/secrets **locaux** (dev). Le contenu est **git-ignoré** — seul ce
README est versionné, pour que le dossier existe à la sortie du clone.

## Gmail Postmaster Tools

Dépose ici la clé JSON du compte de service téléchargée depuis Google Cloud, par ex. :

```
credentials/google-postmaster.json
```

Puis dans `api/.env` :

```
GOOGLE_POSTMASTER_CREDENTIALS_FILE=credentials/google-postmaster.json
```

Le chemin est résolu par rapport à la racine `api/`, donc cette valeur relative
marche quel que soit le dossier depuis lequel tu lances le serveur.

> Pour dépanner un collègue : envoie-lui simplement le fichier JSON, il le pose
> ici avec le même nom et c'est fonctionnel. **Ne commite jamais le JSON.**
>
> En **production**, on n'utilise pas ce dossier : la clé passe par le secret
> GitHub `GOOGLE_POSTMASTER_CREDENTIALS_JSON` (base64) écrit dans le `.env` au déploiement.
