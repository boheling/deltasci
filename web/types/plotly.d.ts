// Ambient declaration for `plotly.js-dist-min`. The published package has no
// types; we only call `react`, `newPlot`, and `purge` so a loose shape is fine.

declare module 'plotly.js-dist-min' {
  type PlotlyTrace = unknown;
  type PlotlyLayout = Record<string, unknown>;
  type PlotlyConfig = Record<string, unknown>;

  interface PlotlyAPI {
    newPlot(
      el: HTMLElement,
      data: PlotlyTrace[],
      layout?: PlotlyLayout,
      config?: PlotlyConfig,
    ): Promise<HTMLElement>;
    react(
      el: HTMLElement,
      data: PlotlyTrace[],
      layout?: PlotlyLayout,
      config?: PlotlyConfig,
    ): Promise<HTMLElement>;
    purge(el: HTMLElement): void;
    relayout(el: HTMLElement, update: PlotlyLayout): Promise<HTMLElement>;
  }

  const Plotly: PlotlyAPI;
  export default Plotly;
}
