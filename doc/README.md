# Système libre de Gestion des Inscriptions des Familles au Transport Scolaire

**School Transport Application Form Tool** est un outil permettant de gérer automatiquement les inscriptions des enfants au transport scolaire d'une école.

Cet outil est **libre** et **gratuit**, sous licence
[Creative Commons CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.fr) (attribution, pas d'utilisation commerciale).

Cet outil utilise plusieurs applications de [_G Suite_](https://www.google.com/intl/fr/nonprofits/offerings/apps-for-nonprofits/) dont vous pouvez bénéficier **gratuitement** en tant qu'**association**.

_Note : si vous êtes une [Association de Parents d'Élèves](https://www.service-public.fr/associations/vosdroits/F1390) (APE), nous vous recommandons de vous enregistrer officiellement comme une [association loi 1901](https://www.associations.gouv.fr/immatriculation.html). La procédure d'enregistrement peut se faire de nos jours [en ligne](https://www.associations.gouv.fr/declaration-initiale.html#cas-e60395-1). Vous pourrez alors faire reconnaître votre association auprès de Google via leur partenaire [Solidatech](https://www.solidatech.fr). L'ensemble de la procédure prend entre 3 à 4 semaines_.

## Étape 1: Formulaire(s) en Ligne

Ce système de gestion des inscriptions des familles au transport scolaire utilise l'application [_Google Forms_](https://www.google.com/intl/fr/forms/about/) qui permet de créer des formulaires en ligne et de collecter automatiquement les réponses fournies par les parents.

Les parents de votre lycée français international ne parlent probablement pas tous la langue française. Malheureusement, _Google Forms_ ne permet toujours pas de créer un formulaire multilingue. Vous aurez à créer autant de formulaires, de structure similaire, que de langues que vous voudrez prendre en charge. Cela ne pose pas de problème pour la suite. C'est exactement la situation que nous avons au Lycée Français International de Saïgon.

| [Français](https://forms.gle/o4zYJ36LZ5FEiaoC6) | [Tiếng Việt](https://forms.gle/crUDHo4xw82F8eyZA) | [English](https://forms.gle/8s16iyzoy5CevDF68) | [한국어](https://forms.gle/rR27CDEu6KeLkRSt8) |
| ----------------------------------------------- | ------------------------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| ![](./doc/google_forms_fra.png)                 | ![](./doc/google_forms_vie.png)                   | ![](./doc/google_forms_eng.png)                | ![](./doc/google_forms_kor.png)               |

### Édition d'un Formulaire en Ligne

#### Sections

![](./doc/google_forms_edition_01.png)

Le formulaire d'inscription de base est découpé en plusieurs sections, permettant à chacune des familles d'inscrire de 1 à 4 enfants et de 1 à 2 parents (ou représentants légaux).

La section d'un enfant permet d'entrer les informations suivantes :

- Nom de famille de l'enfant (type `Short answer`)
- Prénom de l'enfant (type `Short answer`)
- Date de naissance (type `Date`)
- Classe durant l'année scolaire **en cours** (type `Dropdown`)

La liste des classes est celle fournie ci-dessous. Certains établissements français ne font que le primaire et pourront donc réduire cette liste.

| Niveau | Classe                        | Abbréviation |
| ------ | ----------------------------- | ------------ |
| 1      | Toute petite section          | TPS          |
| 2      | Petite section                | PS           |
| 3      | Moyenne section               | MS           |
| 4      | Grande section                | GS           |
| 5      | Cours préparatoire            | CP           |
| 6      | Cours élémentaire, 1ère année | CE1          |
| 7      | Cours élémentaire, 2ème année | CE2          |
| 8      | Cours moyen, 1ère année       | CM1          |
| 9      | Cours moyen, 2ème année       | CM2          |
| 10     | Sixième                       | 6ème         |
| 11     | Cinquième                     | 5ème         |
| 12     | Quatrième                     | 4ème         |
| 13     | Troisième                     | 3ème         |
| 14     | Seconde                       | 2nde         |
| 15     | Première                      | 1ère         |
| 16     | Terminale                     | Tle          |

_Note : la date de naissance est nécessaire pour des raisons de sécurité. Un enfant de moins de 12 n'est pas autorisés (sauf dérogation signée de leurs parents) à descendre du bus scolaire sans la présence obligatoire d'un adulte habilité à venir récupérer cet enfant._

La section d'un parent permet d'entrer les informations suivantes :

- Nom de famille du parent (type `Short answer`)
- Prénom du parent (type `Short answer`)
- Adresse de courriel (type `Short answer` avec validation de la réponse)
- Numéro de téléphone (type `Short answer` avec validation de la réponse)
- Adresse de la résidence des enfants (type `Paragraph` ; champ facultatif dans le cas du 2nd parent, si l'adresse est identique à celle du 1er parent)

| Section Enfant                                   | Section Parent                                    |
| ------------------------------------------------ | ------------------------------------------------- |
| ![](./doc/google_form_edition_child_section.png) | ![](./doc/google_form_edition_parent_section.png) |

### Navigation entre les Sections

La navigation entre les différentes sections du formulaire est dynamique.

Les sections du 1er, 2ème et 3ème enfant comportent une question finale demandant si le parent souhaite ajouter un autre enfant. Si le parent ne souhaite pas ajouter un 2ème, 3ème enfant ou 4ème enfant, le formulaire saute directement à la section du 1er parent.

De façon similaire, la section du 1er parent comporte une question finale demandant si le parent souhaite ajouter un second parent. Si le parent ne souhaite pas ajouter un 2nd parent, le formulaire saute directement à la dernière section.

### Liaison des Formulaires à un unique Tableur

Une fois que vous avez terminé la conception de vos formulaires _Google Forms_, vous allez les liér individuellement à un seul tableur _Google Sheets_ :

![](./doc/google_form_responses_01.png)

Lorsque vous liez le tout premier formulaire, vous devez indiquer que vous souhaitez créer un nouveau tableur _Google Sheets_ :

![](./doc/google_form_responses_02.png)

Par convention, nous renommerons chaque tableau par le code [ISO 639-3:2007 de la langue](https://docs.google.com/spreadsheets/d/1BnrNVSsFbgSuP_ERyAPEZ-LFpvKYfGlREsInTjJVvr4/edit?usp=sharing) correspondant au formulaire associé. Par exemple :

| Nom par défault                          | Nom modifié                              |
| ---------------------------------------- | ---------------------------------------- |
| ![](./doc/google_sheet_responses_03.png) | ![](./doc/google_sheet_responses_02.png) |

Lorsque vous liez les formulaires, vous devez indiquer que vous souhaitez sélectionner le tableur _Google Sheets_ précédemment créé :

| 1. Sélection du Tableur                 | 2. Création automatique du 2nd Tableau   | 3. Renommage du Tableau                  |
| --------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| ![](./doc/google_form_responses_03.png) | ![](./doc/google_sheet_responses_03.png) | ![](./doc/google_sheet_responses_04.png) |

Cependant, outre le fait que le format de chaque tableau, correspondant aux réponses d'un formulaire, n'est guère lisible, les réponses des parents se retrouvent dispersées dans plusieurs tableaux du tableur _Google Sheets_. Nous ne lirons donc pas directement ce document.

## Étape 2: Liste Principale des Enfants et des Parents

Les membres de l'association, généralement non technomanes, vont utiliser un autre document _Google Sheets_ pour gérer les dossiers d'inscription des familles au transport scoliare de l'école. Ce document coloré présente les informations dans un format plus humainement compréhensible :

![](./doc/google_sheet_master_list_01.png)

Les enfants d'une même famille sont listés dans un groupe de lignes, une par enfant. Les parents de ces enfants sont listés sur la même ligne que le premier enfant. Le numéro de dossier d'inscription et la date d'inscription sont également définis sur la même que le premier enfant :

![](./doc/google_sheet_master_list_02.jpg)

Les informations concernant un enfant sont globalement les mêmes que celles saisies par son parent dans l'un des formulaires en ligne :

- Prénom de l'enfant (la première lettre de chaque prénom en majuscule, les autres lettres en minuscule)
- Nom de famille de l'enfant (en lettres majuscules)
- Nom complet de l'enfant (concaténation du prénom et du nom de l'enfant dans l'ordre culturel présumé de l'enfant)
- Date de naissance
- Niveau de la classe de l'enfant durant l'année scolaire en cours

Les informations concernant un parent proviennent également des données saisies par ce parent dans l'un formulaires en ligne, avec quelques autres données calculées :

- Prénom du parent
- Nom de famille du parent
- Nom complet du parent
- Langue du parent (déterminé pour le 1er parent de la langue du formulaire utilisé; déterminé pour le 2nd parent de son nom (e.g. vietnamien) ou par défault de la langue du formulaire utilisé)
- Adresse de courrier électronique (en lettres minuscules)
- Numéro de téléphone (sur 10 chiffres, et préfixé par l'index du pays)
- Adresse de résidence telle qu'entrée par le parent
- Adresse telle que revue par _Google Geocoding API_ (généralement mieux formatée que celle entrée par le parent)
- Coordonnées géographiques (latitude, longitude) correspondant à l'adresse de résidence entrée par le parent
