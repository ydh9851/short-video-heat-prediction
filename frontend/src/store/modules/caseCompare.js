/**
 * 场景对比托盘：把 2~3 个分析场景固定到全局托盘，供任意页面发起并排对比。
 * 只保存轻量快照（id/名称/类别/模型），完整参数以对比接口返回为准；
 * 持久化到 localStorage，刷新页面不丢失。
 */

const STORAGE_KEY = 'caseCompareTray'
const MAX_SIZE = 3

function loadStored () {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list.slice(0, MAX_SIZE) : []
  } catch (e) {
    return []
  }
}

function persist (items) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch (e) { /* 隐私模式等场景下落盘失败不影响内存态 */ }
}

const state = {
  items: loadStored()
}

const mutations = {
  ADD (state, item) {
    if (!item || item.id == null || state.items.some(i => i.id === item.id)) return
    state.items = state.items.concat([{
      id: item.id,
      name: item.name,
      videoCategory: item.videoCategory,
      model: item.model
    }]).slice(0, MAX_SIZE)
    persist(state.items)
  },
  REMOVE (state, id) {
    state.items = state.items.filter(i => i.id !== id)
    persist(state.items)
  },
  CLEAR (state) {
    state.items = []
    persist(state.items)
  }
}

const actions = {
  // 返回 true 表示加入成功；已存在或超过 3 个返回 false
  add ({ state, commit }, item) {
    if (!item || item.id == null) return false
    if (state.items.some(i => i.id === item.id)) return false
    if (state.items.length >= MAX_SIZE) return false
    commit('ADD', item)
    return true
  },
  remove ({ commit }, id) {
    commit('REMOVE', id)
  },
  toggle ({ state, commit }, item) {
    if (!item || item.id == null) return false
    if (state.items.some(i => i.id === item.id)) {
      commit('REMOVE', item.id)
      return false
    }
    if (state.items.length >= MAX_SIZE) return false
    commit('ADD', item)
    return true
  },
  clear ({ commit }) {
    commit('CLEAR')
  }
}

export default {
  namespaced: true,
  state,
  mutations,
  actions
}
