// 「次に処理する 1 枚」だけを持つ入れ物。処理が追いつかないときは古い方を捨てる（溜めない。設計書④-E1 2章）。
export class LatestSlot {
  constructor() {
    this.item = null;
    this.dropped = 0;
  }

  put(item) {
    if (this.item !== null) this.dropped++;
    this.item = item;
  }

  take() {
    const item = this.item;
    this.item = null;
    return item;
  }

  get empty() {
    return this.item === null;
  }
}
