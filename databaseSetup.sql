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

CREATE TABLE crypto.`MetricType` (
  `id` int auto_increment primary key,
  `name` varchar(50) not null,
  `accessKey` varchar(50) not null,
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

INSERT INTO crypto.MetricType (name, accessKey, createdAt, updatedAt)
    VALUES ('price', '["result"]["price"]["last"]', now(), now());

INSERT INTO crypto.MetricType (name, accessKey, createdAt, updatedAt)
    VALUES ('highPriceLast24Hrs','["result"]["price"]["high"]', now(), now());

INSERT INTO crypto.MetricType (name, accessKey, createdAt, updatedAt)
    VALUES ('lowPriceLast24Hrs','["result"]["price"]["low"]', now(), now());

INSERT INTO crypto.MetricType (name, accessKey, createdAt, updatedAt)
    VALUES ('percentChange','["result"]["price"]["change"]["percentage"]', now(), now());

INSERT INTO crypto.MetricType (name, accessKey, createdAt, updatedAt)
    VALUES ('absoluteChange','["result"]["price"]["change"]["absolute"]', now(), now());

INSERT INTO crypto.MetricType (name, accessKey, createdAt, updatedAt)
    VALUES ('volume','["result"]["volume"]', now(), now());

INSERT INTO crypto.MetricType (name, accessKey, createdAt, updatedAt)
    VALUES ('quoteVolume','["result"]["volumeQuote"]', now(), now());

INSERT INTO `crypto`.`User` (`firstName`, `lastName`, `email`, `createdAt`, `updatedAt`)
    VALUES ('Donny', 'Flynn', 'donny@pivasc.com', now(), now());
