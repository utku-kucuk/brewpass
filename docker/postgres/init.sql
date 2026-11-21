-- Runs once, when the database volume is first created.
-- Database-per-service: each service owns its schema and only talks to the others over HTTP.
CREATE DATABASE brewpass_auth;
CREATE DATABASE brewpass_catalog;
CREATE DATABASE brewpass_commerce;
CREATE DATABASE brewpass_payment;
