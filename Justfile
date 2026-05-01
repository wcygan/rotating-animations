set shell := ["bash", "-cu"]

default:
    @just --list

# Run the dev server behind portless (https://rotating-animations.localhost)
dev:
    cd web && bunx portless

# Plain Vite dev server (random port, http)
dev-bare:
    cd web && bun --bun vite dev

build:
    cd web && bun --bun vite build

preview:
    cd web && bun --bun vite preview

test:
    cd web && bun --bun vitest run

install:
    cd web && bun install
