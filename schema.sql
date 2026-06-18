-- ============================================================
--  Celia's Burger — Schema Supabase (PostgreSQL)
--  Proyecto: celias-burger (kiggakculokjznnxdkuk.supabase.co)
--  Ejecutado: 2026-06-15
-- ============================================================

-- Productos
create table productos (
    id      serial primary key,
    codigo  text not null unique,
    nombre  text not null,
    precio  numeric(10,2) not null,
    categoria text,
    activo  boolean not null default true
);

-- Clientes
create table clientes (
    id        serial primary key,
    codigo    text not null unique,
    nombre    text not null,
    celular   text,
    direccion text
);

-- Ventas (cabecera)
create table ventas (
    id        serial primary key,
    fecha     timestamp not null,
    cajero    text not null,
    cliente   text not null,
    tipo      text not null,
    total     numeric(10,2) not null,
    direccion text,
    celular   text,
    metodo    text not null,
    anulada   boolean not null default false
);

-- Ítems de venta (detalle)
create table venta_items (
    id        serial primary key,
    venta_id  integer not null references ventas(id) on delete cascade,
    producto  text not null,
    precio    numeric(10,2) not null
);

-- Índices para consultas rápidas por fecha y venta
create index idx_venta_items_venta_id on venta_items(venta_id);
create index idx_ventas_fecha         on ventas(fecha);
