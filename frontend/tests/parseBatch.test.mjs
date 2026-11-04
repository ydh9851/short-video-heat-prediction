/**
 * 批量预测输入解析的单元测试。
 *
 * 用 Node 内置的 test 运行器（node --test），不引入任何测试框架依赖：
 *   node --test frontend/tests/
 *
 * 这段逻辑原先藏在组件里，只能靠手工点页面验证；抽成纯函数后，
 * 边界情况（空输入、列数不足、非数字、越界、超量）都能被自动覆盖。
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseBatch, MAX_BATCH_ROWS } from '../src/views/predict/batch/parseBatch.mjs'

test('空输入给出明确提示', () => {
  const { items, error } = parseBatch('')
  assert.equal(items.length, 0)
  assert.equal(error, '请至少输入一行数据')
})

test('空白行被忽略，合法行被解析', () => {
  const { items, error } = parseBatch('\n美食,50000,20,5,6\n\n  音乐,1200,15,2,9  \n')
  assert.equal(error, '')
  assert.equal(items.length, 2)
  assert.deepEqual(items[0], {
    videoCategory: '美食', authorFans: 50000, publishHour: 20, publishWeekday: 5, publishMonth: 6
  })
  assert.equal(items[1].videoCategory, '音乐')
  assert.equal(items[1].authorFans, 1200)
})

test('中文逗号同样可用', () => {
  const { items, error } = parseBatch('美食，50000，20，5，6')
  assert.equal(error, '')
  assert.equal(items.length, 1)
  assert.equal(items[0].authorFans, 50000)
})

test('列数不足时报出具体行号', () => {
  const { items, error } = parseBatch('美食,50000,20\n音乐,1200,15,2,9')
  assert.equal(items.length, 0)
  assert.match(error, /第 1 行/)
})

test('非数字字段被拦截', () => {
  const { error } = parseBatch('美食,五万,20,5,6')
  assert.match(error, /第 1 行含非数字字段/)
})

test('取值越界被拦截并说明范围', () => {
  assert.match(parseBatch('美食,100,24,5,6').error, /取值超出范围/)
  assert.match(parseBatch('美食,100,20,7,6').error, /取值超出范围/)
  assert.match(parseBatch('美食,100,20,5,13').error, /取值超出范围/)
})

test('超出条数上限被拦截', () => {
  const many = Array.from({ length: MAX_BATCH_ROWS + 1 }, () => '美食,100,20,5,6').join('\n')
  const { items, error } = parseBatch(many)
  assert.equal(items.length, 0)
  assert.match(error, /一次最多/)
})

test('恰好等于上限时允许通过', () => {
  const ok = Array.from({ length: MAX_BATCH_ROWS }, () => '美食,100,20,5,6').join('\n')
  const { items, error } = parseBatch(ok)
  assert.equal(error, '')
  assert.equal(items.length, MAX_BATCH_ROWS)
})