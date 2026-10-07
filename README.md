# Administration Platform Backend

FastAPI odpowiada za autoryzację Azure Entra, kontrolę dostępu do zgłoszeń, historię zmian, czat i kolejkę powiadomień. Dane zgłoszeń pozostają w Strapi.

## Konfiguracja

Skopiuj `.env.example` do `.env` i ustaw:

```env
DB_CONNECT=localhost
DB_PORT=5433
DB_USER=administration
DB_PASSWORD=...
DB_NAME=administration_backend

STRAPI_URL=https://cms.example.com
STRAPI_KEY=...

AZURE_TENANT_ID=00000000-0000-0000-0000-000000000000
AZURE_AUDIENCE=00000000-0000-0000-0000-000000000000
AZURE_REQUIRED_SCOPE=access_as_user
AZURE_ALLOWED_CLIENT_IDS=00000000-0000-0000-0000-000000000000
```

`STRAPI_KEY` powinien być serwerowym tokenem Content API. Nie przekazuj go do Next.js ani przeglądarki. Token potrzebuje co najmniej `Requests.find` i `Requests.findOne` oraz dostępu do relacji używanych przez populate: `requested_by`, `assigned_to`, `service_task` i `main_location`.

## Azure Entra

1. Utwórz osobną App Registration dla backendowego API.
2. W `Expose an API` ustaw Application ID URI, np. `api://<API_CLIENT_ID>`, i delegated scope `access_as_user`.
3. W manifeście API użyj tokenów dostępowych v2 (`requestedAccessTokenVersion: 2`).
4. Dodaj App Roles: `Employee`, `RequestAgent`, `RequestAdmin` i przypisz je użytkownikom lub grupom.
5. `AZURE_AUDIENCE` ustaw na wartość claimu `aud` prawdziwego access tokenu. Dla tokenu v2 do własnego API jest to zwykle Application (client) ID rejestracji backendu (GUID), nie client ID frontendu.
6. `AZURE_ALLOWED_CLIENT_IDS` zawiera rozdzielone przecinkiem Application (client) ID aplikacji, które mogą wywoływać API, np. rejestrację Next.js. Backend porównuje je z claimem `azp`/`appid`.
7. Frontend prosi o scope `api://<API_CLIENT_ID>/access_as_user` i wysyła access token jako `Authorization: Bearer <token>`.

Backend weryfikuje podpis przez JWKS Microsoftu, `issuer`, `audience`, `tid`, czas ważności, delegated scope, aplikację kliencką oraz App Role. Identyfikator użytkownika pochodzi wyłącznie z claimu `oid`.

## Uruchomienie

```powershell
python -m pip install -r requirements.txt
python -m alembic upgrade head
python main.py
```

Swagger: `http://127.0.0.1:8000/docs`.

## Endpointy

```text
GET  /api/v1/auth/me
GET  /api/v1/requests/mine
GET  /api/v1/requests/{document_id}
GET  /api/v1/requests/{document_id}/events
POST /api/v1/requests/{document_id}/events                 RequestAgent/Admin
POST /api/v1/requests/{document_id}/conversation           RequestAgent/Admin
GET  /api/v1/conversations/{conversation_id}/messages
POST /api/v1/conversations/{conversation_id}/messages
```

Użytkownik nie może otworzyć rozmowy. Po otwarciu jej przez administrację może odczytywać i wysyłać wiadomości wyłącznie w swoim zgłoszeniu.

`notification_outbox` przechowuje zadania mailowe. Wysyłanie wymaga osobnego workera, który pobierze rekordy `pending`, wyśle wiadomość i ustawi `sent_at` oraz `delivery_status`.