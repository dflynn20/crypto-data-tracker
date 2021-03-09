-- Here is the MySQL code to create the backend for the application.

-- For more details, review the Entity Relationship Diagram here:
-- https://drive.google.com/file/d/1_ltuClV3AReFugKyGAiPhEupvrrHWlke/view?usp=sharing

CREATE SCHEMA crypto;

CREATE TABLE crypto.`User` (
  `id` int auto_increment primary key,
  `firstName` varchar(50) not null,
  `lastName` varchar(50) not null,
  `email` varchar(255) default null,
  `createdAt` datetime not null,
  `updatedAt` datetime not null,
  `deletedAt` datetime default null
);

CREATE TABLE crypto.`MetricValue` (
  `id` int auto_increment primary key,
  `currencyPairMetricId` int not null,
  `value` float not null,
  `queriedAt` datetime not null
);

CREATE TABLE crypto.`CurrencyPairMetric` (
  `id` int auto_increment primary key,
  `pair` varchar(50) not null,
  `market` varchar(50) not null,
  `metricTypeId` int not null
);

CREATE TABLE crypto.`UserCurrencyPairMetric` (
  `id` int auto_increment primary key,
  `userId` int not null,
  `createdAt` datetime not null,
  `deletedAt` datetime default null
);

CREATE TABLE crypto.`MetricType` (
  `id` int auto_increment primary key,
  `name` varchar(50) not null,
  `firstLevel` varchar(50) not null,
  `secondLevel` varchar(50) default null,
  `thirdLevel` varchar(50) default null,
  `createdAt` datetime not null,
  `updatedAt` datetime not null,
  `deletedAt` datetime default null
);

INSERT INTO crypto.MetricType (name, firstLevel, secondLevel, createdAt, updatedAt)
    VALUES ('price', 'price', 'last', now(), now());

INSERT INTO crypto.MetricType (name, firstLevel, secondLevel, createdAt, updatedAt)
    VALUES ('highPriceLast24Hrs', 'price', 'high', now(), now());

INSERT INTO crypto.MetricType (name, firstLevel, secondLevel, createdAt, updatedAt)
    VALUES ('lowPriceLast24Hrs', 'price', 'low', now(), now());

INSERT INTO crypto.MetricType (name, firstLevel, secondLevel, thirdLevel, createdAt, updatedAt)
    VALUES ('percentChange','price','change','percentage', now(), now());

INSERT INTO crypto.MetricType (name, firstLevel, secondLevel, thirdLevel, createdAt, updatedAt)
    VALUES ('absoluteChange','price','change','absolute', now(), now());

INSERT INTO crypto.MetricType (name, firstLevel, createdAt, updatedAt)
    VALUES ('volume', 'volume', now(), now());

INSERT INTO crypto.MetricType (name, firstLevel, createdAt, updatedAt)
    VALUES ('quoteVolume','volumeQuote', now(), now());

INSERT INTO `crypto`.`User` (`firstName`, `lastName`, `email`, `createdAt`, `updatedAt`)
    VALUES ('Donny', 'Flynn', 'donny@pivasc.com', now(), now());
