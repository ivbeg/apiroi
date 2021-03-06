# API для РОИ

API для Российской общественной инициативы www.roi.ru 


# Цель
Обеспечить непрерывный мониторинг Российской общественной инициативы и раскрытие информацие по истории голосования в машиночитаемом виде.

# Текущий статус

1. Данные выгружены за 2 ноября 2013 года - http://hubofdata.ru/dataset/roi-dump
1. Дорабатывается скрипт регулярного обновления данных.

# Основные понятия
## Объекты

* petition - петиция (инициатива)
* user - пользователь подавший инициативу
* probe - проба данных на получение актуальных данных по голосованиям

### Объект petition

* _id - идентификатор, строка
* url - ссылка на сайте РОИ
* uniqid - уникальный идентификатор инициативы в системе (человекочитаемый, например: "Инициатива № 77Ф333")
* slug - укороченный текст из ссылки - уникальный идентификатор
* name - название инициативы
* description - подробный текст инициативы
* jurisdiction - уровень инициативы
* start_date - дата публикации инициативы
* end_date - дата публикации инициативы
* probe_date - дата последнего снятия информации об инициативе
* votes - число голосов за
* topic_id - тема инициативы
* autor_id - идентификатор пользователя разместившего петицию

Источник: страница с описание инициативы 

**Пример**

https://www.roi.ru/poll/petition/problemy-potrebitelej-i-plohoj-servis/obyazat-kazhduyu-upravlyayushuyu-kompaniyu-uk-tszh-kazhduyu-strukturu-zhkh-imet-svoj-sajt-v-sisteme-internet/



### Объект user
* id - название
* petitions - список петиций размещенных пользователем


Источник: страница инициатив пользователя

**Пример**
https://www.roi.ru/poll/?pl1_uid=1612


### Объект probe
* id - искусственный уникальный ключ
* probe_dt - дата и время пробы
* petition - уникальный идентификатор петиции в системе
* votes_yes - голосов за
* votes_no - голосов против
* probe_status - статус пробы, успешен ли сбор данных

Система создает пробы самостоятельно путем регулярных опросов страниц РОИ


## Словари

* level - уровень инициативы (уровень гос-ва)
* status - статус инициативы - на голосовании, на рассмотрении, решение принято
* topic - раздел к которой относится петиция


## Точки доступа к API

	/roi/v1/users - список пользователей с возможностью делать запросы
	/roi/v1/users/[id] - профиль отдельного пользователя
	/roi/v1/petitions - список всех петийций с возможностью делать запросы
	/roi/v1/petitions/[id] - информация по конкретной петиции
	/roi/v1/petitions/[id]/votes - история голосования по петиции по пробам. С возможностью пролистать все пробы
	/roi/v1/dicts/topic - словарь разделов
	/roi/v1/dicts/status - словарь статусов
	/roi/v1/dicts/level	 - словарь уровней

## Стратегии обновления

### Первоначальное наполнение

1. Итеративная выгрузка данных по убыванию: https://www.roi.ru/poll/?s_f_1=user_f_29=DESC& параметр страницы передается как page_19= за один раз выводится 10 петиций. При первом запросе необходимо сохранить общее число петиций, а далее листать страницы.
2. Для каждой петиции необходимо сохранить информацию и сделать пробу данных.
3. Из страницы петиции выявить ID пользователя и заполнить коллекцию пользователей

Частота: однократно


### Обновление списка петиций 

1. Обращение к https://www.roi.ru/poll/?s_f_1=user_f_29=DESC& и выгрузка новых петиций.

Частота: 1 раз в 4 часа, 6 раз в сутки, 180 раз в месяц

### Обновление данных о голосовании

1. Обновление информации о числе проголосовавших

Итеративное обновление данных по убыванию: https://www.roi.ru/poll/?s_f_1=user_f_29=DESC& параметр страницы передается как page_19= за один раз выводится 10 петиций. При первом запросе необходимо сохранить общее число петиций, а далее листать страницы.

Частота: 1 раз в 1 час, число обращений = (число петиций / 10) + 1
Для 2005 петиций - это около abs(2005/10) + 1 = 201 запрос за час и 24*201 = 4824 в сутки.

1. Обращение к каждой петиции в статусе "Идет голосование" и выгрузка статистики голосования

Частота: 1 раз в сутки на петицию.
Для 2000 петиций - это около 2000 тысячи обращений в сутки. Если каждый час - то около 48 тысяч обращений в сутки

## Структура ссылок сайта ROI

### Страница петиции

**Структура ссылки**

	http://www.roi.ru/poll/petition/[category_slug]/[slug]
	
* category_slug - часть ссылки указывающая на категорию
* slug - часть ссылки указывающая на уникальное название петиции

**Пример**
	
	https://www.roi.ru/poll/petition/transport-i-dorogi/otmena-prava-prioritetnogo-proezda-vseh-avtomobilej-krome-avtomobilej-operativnyh-sluzhb/


### Стратница автора


**Структура ссылки**

	https://www.roi.ru/poll/?pl1_uid=[user_id]
	
* user_id - уникальный идентификатор пользователя

**Пример**
	
	https://www.roi.ru/poll/?pl1_uid=1929
	
