/**
 * LocalStorage 封装工具
 */

/**
 * 存储数据到 localStorage
 */
export function setLocalStorage<T>(key: string, value: T): void {
  try {
    const serialized = JSON.stringify(value);
    localStorage.setItem(key, serialized);
  } catch (error) {
    console.error(`Failed to save to localStorage: ${key}`, error);
  }
}

/**
 * 从 localStorage 读取数据
 */
export function getLocalStorage<T>(key: string): T | null {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
  } catch (error) {
    console.error(`Failed to read from localStorage: ${key}`, error);
    return null;
  }
}

/**
 * 从 localStorage 删除数据
 */
export function removeLocalStorage(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (error) {
    console.error(`Failed to remove from localStorage: ${key}`, error);
  }
}

/**
 * 清空 localStorage
 */
export function clearLocalStorage(): void {
  try {
    localStorage.clear();
  } catch (error) {
    console.error('Failed to clear localStorage', error);
  }
}
