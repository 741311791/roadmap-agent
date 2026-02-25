/**
 * next-intl 类型定义
 * 
 * 确保翻译key的类型安全
 */

type Messages = typeof import('../messages/en.json');
declare interface IntlMessages extends Messages {}
