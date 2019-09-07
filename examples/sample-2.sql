CREATE TABLE shipto (
	name FK string NOT NULL
	,address FK string NOT NULL
	,city FK string NOT NULL
	,country FK string NOT NULL
	);

CREATE TABLE item (
	title FK string NOT NULL
	,note FK string
	,quantity FK positiveInteger NOT NULL
	,price FK DECIMAL NOT NULL
	);

CREATE TABLE shiporder (orderperson FK string NOT NULL);

CREATE TABLE examples_sample_2 (
	orderperson VARCHAR NOT NULL
	,name VARCHAR NOT NULL
	,address VARCHAR NOT NULL
	,city VARCHAR NOT NULL
	,country VARCHAR NOT NULL
	,title VARCHAR NOT NULL
	,note VARCHAR NOT NULL
	,quantity INTEGER NOT NULL
	,price NUMERIC NOT NULL
	);
