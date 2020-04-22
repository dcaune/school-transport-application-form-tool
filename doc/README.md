# Système libre de Gestion des Inscriptions des Familles au Transport Scolaire

**School Transport Application Form Tool** est un outil permettant de gérer automatiquement les inscriptions des enfants au transport scolaire d'une école.

Cet outil est **libre** et **gratuit**, sous licence
[Creative Commons CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.fr) (attribution, pas d'utilisation commerciale).

Cet outil utilise les [outils _G Suite_](https://www.google.com/intl/fr/nonprofits/offerings/apps-for-nonprofits/) dont vous pouvez bénéficier **gratuitement** en tant qu'**association**.

_Note : si vous êtes une [Association de Parents d'Élèves](https://www.service-public.fr/associations/vosdroits/F1390) (APE), nous vous recommandons de vous enregistrer officiellement comme une [association loi 1901](https://www.associations.gouv.fr/immatriculation.html). La procédure d'enregistrement peut se faire de nos jours [en ligne](https://www.associations.gouv.fr/declaration-initiale.html#cas-e60395-1). Vous pourrez alors faire reconnaître votre association auprès de Google via leur partenaire [Solidatech](https://www.solidatech.fr). L'ensemble de la procédure prend entre 3 à 4 semaines_.

## Étape 1: Formulaire(s) en Ligne

Ce système de gestion des inscriptions des familles au transport scolaire utilise l'application [_Google Forms_](https://www.google.com/intl/fr/forms/about/) qui permet de créer des formulaires en ligne et de collecter automatiquement les réponses fournies par les parents.

Les parents de votre lycée français international ne parlent probablement pas tous la langue française. Malheureusement, _Google Forms_ ne permet toujours pas de créer un formulaire multilingue. Vous aurez à créer autant de formulaires, de structure similaire, que de langues que vous voudrez prendre en charge. Cela ne pose pas de problème pour la suite. C'est exactement la situation que nous avons au Lycée Français International de Saïgon.

| [Français](https://forms.gle/o4zYJ36LZ5FEiaoC6) | [Tiếng Việt](https://forms.gle/crUDHo4xw82F8eyZA) | [English](https://forms.gle/8s16iyzoy5CevDF68) | [한국어](https://forms.gle/rR27CDEu6KeLkRSt8) |
| ----------------------------------------------- | ------------------------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| ![](./doc/google_forms_fra.png)                 | ![](./doc/google_forms_vie.png)                   | ![](./doc/google_forms_eng.png)                | ![](./doc/google_forms_kor.png)               |

### Édition du Formulaire en Ligne

![](./doc/google_forms_edition_01.png)

Le formulaire d'inscription de base est découpé en plusieurs sections, permettant à chacune des familles d'inscrire de 1 à 4 enfants et de 1 à 2 parents (ou représentants légaux).

La section d'un enfant permet d'entrer les informations suivantes :

- Nom de famille de l'enfant (type `Short answer`)
- Prénom de l'enfant (type `Short answer`)
- Date de naissance (type `Date`)
- Classe durant l'année scolaire **en cours** (type `Dropdown`)

La section d'un parent permet d'entrer les informations suivantes :

- Nom de famille du parent (type `Short answer`)
- Prénom du parent (type `Short answer`)
- Adresse de courriel (type `Short answer` avec validation de la réponse)
- Numéro de téléphone (type `Short answer` avec validation de la réponse)
- Adresse de la résidence des enfants (facultative dans le cas du 2nd parent, si l'adresse est identique à celle du 1er parent)

| Section Enfant                                 | Section Parent                                    |
| ---------------------------------------------- | ------------------------------------------------- |
| ![](doc/google_form_edition_child_section.png) | ![](./doc/google_form_edition_parent_section.png) |
