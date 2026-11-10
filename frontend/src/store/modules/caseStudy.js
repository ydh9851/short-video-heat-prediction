/**
 * 分析场景（Case）跨页上下文：
 * 一个场景承载一次分析的完整先验输入（模型、类别、粉丝数、发布时刻），
 * 用户在「数据样本 / 预测 / 归因」任一页面选定或保存场景后，
 * 其他页面自动复用，实现验收主线「全流程不重复输入」。
 * 持久化到 localStorage，刷新不丢失。
 */

const STORAGE_KEY = 'currentCase'

function loadStored () {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

const state = {
  current: loadStored()
}

const mutations = {
  SET_CURRENT (state, caseObj) {
    state.current = caseObj
    try {
      if (caseObj) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(caseObj))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch (e) { /* 隐私模式等场景下落盘失败不影响内存态 */ }
  }
}

const actions = {
  setCurrent ({ commit }, caseObj) {
    commit('SET_CURRENT', caseObj)
  },
  clearCurrent ({ commit }) {
    commit('SET_CURRENT', null)
  }
}

export default {
  namespaced: true,
  state,
  mutations,
  actions
}
