import { readFile, writeFile } from 'node:fs/promises'

const path = new URL('../src/schema.ts', import.meta.url)
const source = await readFile(path, 'utf8')
const withoutGeneratedComments = source.replace(/\/\*\*[\s\S]*?\*\/\s*/g, '')
await writeFile(path, withoutGeneratedComments, 'utf8')
