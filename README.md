# ValutaTrade Hub

Итоговый проект курса «Программирование на Python»: консольная платформа
для отслеживания и симуляции торговли фиатными валютами и криптовалютами.
Пользователи регистрируются, управляют портфелем кошельков, совершают
покупку и продажу, а курсы подтягиваются отдельным сервисом парсинга
из публичных API и кэшируются локально.

## Структура проекта

```
finalproject_Lapin_M26-555/
├── data/                        # JSON-хранилища (создаются при работе)
│   ├── users.json               # пользователи
│   ├── portfolios.json          # портфели и кошельки
│   ├── rates.json               # кэш последних курсов
│   └── exchange_rates.json      # история измерений курсов
├── valutatrade_hub/
│   ├── logging_config.py        # логирование с ротацией
│   ├── decorators.py            # декоратор @log_action
│   ├── core/
│   │   ├── currencies.py        # иерархия Currency: Fiat/Crypto
│   │   ├── exceptions.py        # доменные исключения
│   │   ├── models.py            # User, Wallet, Portfolio
│   │   ├── usecases.py          # бизнес-логика
│   │   └── utils.py             # валидации и форматирование
│   ├── infra/
│   │   ├── settings.py          # Singleton SettingsLoader
│   │   └── database.py          # Singleton DatabaseManager
│   ├── parser_service/
│   │   ├── config.py            # настройки API (ключ из окружения)
│   │   ├── api_clients.py       # CoinGecko и ExchangeRate-API
│   │   ├── storage.py           # кэш и история курсов
│   │   └── updater.py           # RatesUpdater
│   └── cli/
│       └── interface.py         # команды пользователя
├── main.py
├── Makefile
├── pyproject.toml
└── README.md
```

## Установка

```bash
make install
```

или `uv sync`.

## Запуск

```bash
make run
```

или `uv run python main.py` (после установки пакета также доступна
команда `valutatrade`).

## Проверка стиля

```bash
make lint
```

## Команды

```
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=1). Войдите: login --username alice --password ****
> login --username alice --password 1234
Вы вошли как 'alice'
> buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 76046.00 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 3,802.30 USD
> sell --currency BTC --amount 0.02
Продажа выполнена: 0.0200 BTC по курсу 76046.00 USD/BTC
Изменения в портфеле:
- BTC: было 0.0500 → стало 0.0300
Оценочная выручка: 1,520.92 USD
> show-portfolio
Портфель пользователя 'alice' (база: USD):
- BTC: 0.0300  → 2281.38 USD
---------------------------------
ИТОГО: 2,281.38 USD
> get-rate --from USD --to BTC
Курс USD→BTC: 0.00001315 (обновлено: 2026-11-07 08:03:33)
Обратный курс BTC→USD: 76046.00
```

Также доступны:

- `show-portfolio --base EUR` - портфель в другой базовой валюте;
- `update-rates [--source coingecko|exchangerate]` - обновить курсы;
- `show-rates [--currency BTC] [--top 3] [--base EUR]` - курсы из кэша;
- `help` - список команд.

## Демонстрация работы

![Демонстрация полного цикла работы](demo.gif)

Интерактивная запись в плеере asciinema: [https://asciinema.org/a/aeSEIKuojDLWpniz](https://asciinema.org/a/aeSEIKuojDLWpniz)

В записи виден весь цикл: регистрация и вход, обновление шести курсов
из двух API, получение курса, покупка и продажа (в том числе с ошибками:
занятое имя, неверный пароль, нехватка средств, неизвестная валюта),
портфель в базах USD и EUR и список курсов.

## Кэш курсов и TTL

Parser Service сохраняет последние курсы в `data/rates.json`, а каждую
запись добавляет в историю `data/exchange_rates.json`. Основной сервис
считает кэш свежим `rates_ttl_seconds` секунд (300 по умолчанию,
настраивается в секции `[tool.valutatrade]` файла pyproject.toml). Когда
кэш устаревает, команды сами запускают обновление или сообщают, что курс
недоступен.

## Parser Service и ключ API

Курсы криптовалют (BTC, ETH, SOL) приходят из CoinGecko - ключ не нужен.
Курсы фиата (EUR, GBP, RUB) - из ExchangeRate-API, для него нужен
персональный ключ. Задайте его в переменной окружения, ключ нигде
не хранится и в git не попадает:

```bash
export EXCHANGERATE_API_KEY=ваш_ключ
uv run python main.py
> update-rates
```

Если ключ не задан или внешний API недоступен, обновление продолжается
с остальных источников, а детали пишутся в logs/parser.log.

## Логи

Действия пользователей пишутся декоратором `@log_action` в
`logs/actions.log`, работа парсера - в `logs/parser.log`. Файлы
ротируются при достижении 512 КБ.
