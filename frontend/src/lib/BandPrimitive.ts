import type {
  ISeriesPrimitive,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  SeriesAttachedParameter,
  Time,
  ISeriesApi,
  IChartApiBase,
  SeriesType,
} from 'lightweight-charts'
import type { CanvasRenderingTarget2D } from 'fancy-canvas'
import type { ChartPointAgg } from './api'

interface BandPoint {
  x: number
  p25y: number
  p75y: number
}

class BandRenderer implements IPrimitivePaneRenderer {
  constructor(
    private readonly _buyPts: BandPoint[],
    private readonly _sellPts: BandPoint[],
  ) {}

  draw(target: CanvasRenderingTarget2D): void {
    target.useMediaCoordinateSpace(({ context: ctx }) => {
      this._fill(ctx, this._buyPts, 'rgba(239,68,68,0.10)')
      this._fill(ctx, this._sellPts, 'rgba(247,166,0,0.10)')
    })
  }

  private _fill(ctx: CanvasRenderingContext2D, pts: BandPoint[], color: string): void {
    if (pts.length < 2) return
    ctx.save()
    ctx.beginPath()
    ctx.moveTo(pts[0].x, pts[0].p75y)
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].p75y)
    for (let i = pts.length - 1; i >= 0; i--) ctx.lineTo(pts[i].x, pts[i].p25y)
    ctx.closePath()
    ctx.fillStyle = color
    ctx.fill()
    ctx.restore()
  }
}

class BandPaneView implements IPrimitivePaneView {
  constructor(private readonly _prim: BandPrimitive) {}

  renderer(): IPrimitivePaneRenderer | null {
    return new BandRenderer(this._prim._buyPts, this._prim._sellPts)
  }
}

export class BandPrimitive implements ISeriesPrimitive<Time> {
  _buyPts: BandPoint[] = []
  _sellPts: BandPoint[] = []

  private _chart: IChartApiBase<Time> | null = null
  private _series: ISeriesApi<SeriesType, Time> | null = null
  private _requestUpdate: (() => void) | null = null
  private _data: ChartPointAgg[] = []
  private _visible = false
  private readonly _views: IPrimitivePaneView[] = [new BandPaneView(this)]

  attached(params: SeriesAttachedParameter<Time>): void {
    this._chart = params.chart
    this._series = params.series as ISeriesApi<SeriesType, Time>
    this._requestUpdate = params.requestUpdate
  }

  detached(): void {
    this._chart = null
    this._series = null
    this._requestUpdate = null
  }

  updateData(data: ChartPointAgg[]): void {
    this._data = data
  }

  setVisible(v: boolean): void {
    this._visible = v
  }

  requestUpdate(): void {
    this._requestUpdate?.()
  }

  updateAllViews(): void {
    this._buyPts = []
    this._sellPts = []
    if (!this._visible || !this._chart || !this._series) return

    const ts = this._chart.timeScale()
    for (const p of this._data) {
      const x = ts.timeToCoordinate(p.ts as unknown as Time)
      if (x === null) continue

      if (p.buy_p25 != null && p.buy_p75 != null) {
        const lo = this._series.priceToCoordinate(p.buy_p25)
        const hi = this._series.priceToCoordinate(p.buy_p75)
        if (lo !== null && hi !== null) this._buyPts.push({ x, p25y: lo, p75y: hi })
      }

      if (p.sell_p25 != null && p.sell_p75 != null) {
        const lo = this._series.priceToCoordinate(p.sell_p25)
        const hi = this._series.priceToCoordinate(p.sell_p75)
        if (lo !== null && hi !== null) this._sellPts.push({ x, p25y: lo, p75y: hi })
      }
    }
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return this._views
  }
}
