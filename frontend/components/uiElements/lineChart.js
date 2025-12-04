"use client";
import * as d3 from "d3";
import { useState, useRef, useEffect } from "react";

// css
import "@/style/uiElements/linechart.scss";

// utils
import { shortenMonths } from "@/utils/dateUtils";

export default function LineChart({
  data = [30, 40, 60, 20, 40, 100, 70],
  xLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
  graphWidth = 700,
  graphHeight = 350,
  margin = { top: 0, right: 0, bottom: 0, left: 0 },
  title = "",
  currValue = "",
  percentage = "",
  amount = "",
  currency = "",
}) {
  xLabels = shortenMonths(xLabels);
  // currValue = data[data.length - 1].toFixed();

  // validate data
  data = data.map((d) => (d ? d : 0));

  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  const innerWidth = dimensions.width - margin.left - margin.right;
  const innerHeight = dimensions.height - margin.top - margin.bottom;

  const xScale = d3
    .scaleLinear()
    .domain([0, data.length - 1])
    .range([0, innerWidth]);

  const yMin = d3.min(data);
  const yMax = d3.max(data);
  const yPadding = (yMax - yMin) * 0.2;
  const yScale = d3
    .scaleLinear()
    .domain([yMin - yPadding, yMax + yPadding]) // same domain
    .nice()
    .range([innerHeight, 40]);

  const line = d3
    .line()
    .x((d, i) => xScale(i))
    .y((d) => yScale(d))
    .curve(d3.curveMonotoneX);

  const area = d3
    .area()
    .x((d, i) => xScale(i))
    .y0(innerHeight)
    .y1((d) => yScale(d))
    .curve(d3.curveMonotoneX);

  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({
        width: width, // use container width
        height: graphHeight || height, // optionally fixed height
      });
    });

    resizeObserver.observe(containerRef.current);

    return () => resizeObserver.disconnect();
  }, [graphHeight]);

  const handleMouseMove = (e) => {
    if (!svgRef.current || !containerRef.current) return;

    const svgRect = svgRef.current.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();

    const graphX = e.clientX - svgRect.left;
    const graphY = e.clientY - svgRect.top;

    if (
      graphX < 0 ||
      graphX > innerWidth ||
      graphY < 0 ||
      graphY > innerHeight
    ) {
      setHoveredPoint(null);
      return;
    }

    const xValue = xScale.invert(graphX);
    const nearestIndex = Math.round(xValue);
    const clampedIndex = Math.max(0, Math.min(data.length - 1, nearestIndex));

    const yValue = data[clampedIndex];
    const svgGraphX = xScale(clampedIndex);
    const svgGraphY = yScale(yValue);

    const left = svgRect.left - containerRect.left + margin.left + svgGraphX;
    const top = svgRect.top - containerRect.top + margin.top + svgGraphY;

    setHoveredPoint({
      xValue: clampedIndex,
      value: yValue,
      svgX: svgGraphX,
      svgY: svgGraphY,
      left,
      top,
      label: xLabels[clampedIndex],
    });
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
  };

  const switchData = (e) => {
    const target = e.target;
    target.parentNode.querySelectorAll("span").forEach((span) => {
      span.classList.remove("_active");
    });
    target.classList.add("_active");
  };

  function shortenText(input, maxLength) {
    if (!input) return "";

    const words = input.split(" ");
    if (words.length <= 3) return input;

    return input.length > maxLength
      ? input.slice(0, maxLength - 3) + "..."
      : input;
  }

  return (
    <div
      className="d3_container linechart"
      ref={containerRef}
      style={{ position: "relative" }}
    >
      <svg
        width={dimensions.width}
        height={dimensions.height}
        ref={svgRef}
        style={{
          display: "block",
          margin: "0 auto",
          background: "rgb(31,31,31)",
          borderRadius: 8,
        }}
      >
        {/* group translated by margins */}
        <g transform={`translate(${margin.left},${margin.top})`}>
          {/* invisible rect overlay to capture pointer events inside graph area */}
          <rect
            x={0}
            y={0}
            width={innerWidth}
            height={innerHeight}
            fill="transparent"
            onMouseMove={handleMouseMove} // listen on the rect (graph area)
            onMouseLeave={handleMouseLeave}
          />

          {/* defs for gradient */}
          <defs>
            <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00CB7D" stopOpacity={0.4} />
              <stop offset="40%" stopColor="#00CB7D" stopOpacity={0.2} />
              <stop offset="60%" stopColor="#00CB7D" stopOpacity={0.1} />
              <stop offset="80%" stopColor="#00CB7D" stopOpacity={0.0} />
              <stop offset="100%" stopColor="#00CB7D" stopOpacity={0.0} />
            </linearGradient>
          </defs>

          {/* area (gradient) */}
          <path
            d={area(data)}
            fill="url(#gradient)"
            style={{ pointerEvents: "none" }}
          />

          {/* line on top */}
          <path d={line(data)} fill="none" stroke="#00CB7D" strokeWidth="1" />

          {/* grids exlude the last one*/}
          {yScale.ticks(5).map((tick, i, arr) => (
            (i === arr.length - 1 || i === 0) ? null : (
              <line
                className="d3_y_grid"
                key={tick}
                x1={0}
                x2={innerWidth}
                y1={yScale(tick)}
                y2={yScale(tick)}
                stroke="rgba(255, 255, 255, 0.04)"
              />
            )
          ))}
          {xScale.ticks(data.length).map((tick, index) => (
            <line
              className="d3_x_grid"
              key={tick}
              y1={0}
              y2={innerHeight}
              x1={xScale(tick)}
              x2={xScale(tick)}
              stroke="rgba(255, 255, 255, 0.04)"
            />
          ))}

          {/* X axis labels (bottom) */}
          <g className="d3_xaxis" transform={`translate(0,${innerHeight})`}>
            {xLabels.map((label, i) => {
              const step = Math.ceil(data.length / 7); // show ~7 labels max
              if (i % step !== 0 && i !== data.length - 1) return null;
              return (
                <g key={i} transform={`translate(${xScale(i)},0)`}>
                  <text dy="-4%" dx="5%" textAnchor="middle" fill="#81827e" opacity={0.6}>
                    {label}
                  </text>
                </g>
              );
            })}
          </g>

          {/* Y axis labels (left) */}
          <g className="d3_yaxis" transform={`translate(15,0)`}>
            {yScale.ticks(5).map((tick) => (
              <g key={tick} transform={`translate(0,${yScale(tick)})`}>
                <text
                  dx="5%"
                  dy="-10"
                  textAnchor="end"
                  fill="#81827e"
                  opacity={0.6}
                >
                  {currency ? `${currency}` : ""}
                  {tick}
                </text>
              </g>
            ))}
          </g>

          {/* vertical guide line + focus circle (draw inside the SVG using svg coords) */}
          {hoveredPoint && (
            <>
              <line
                x1={hoveredPoint.svgX}
                x2={hoveredPoint.svgX}
                y1={0}
                y2={innerHeight}
                stroke="#a6a6a67a"
                strokeWidth={1}
                pointerEvents="none"
              />
            </>
          )}
        </g>
      </svg>

      {title && (
        <div className="d3_data_details">
          <div className="_wrap">
            <img className="_logo" src="/next_images/statement_logo.svg" />
            <div className="data_display">
              <h2>
                {shortenText(title, 30)}{" "}
                {currValue && <span>{`$${currValue}`}</span>}
              </h2>
              {percentage && (
                <p>
                  {amount && <span>{`$ ${amount}`}</span>}
                  <span>
                    <img src="/next_images/increment.svg" />
                    {percentage}
                  </span>
                </p>
              )}
            </div>
          </div>
          <div className="d3_data_switch">
            <span onClick={switchData}>1D</span>
            <span onClick={switchData}>1W</span>
            <span onClick={switchData}>1M</span>
            <span onClick={switchData}>3M</span>
            <span onClick={switchData}>1Y</span>
          </div>
        </div>
      )}

      {/* Tooltip DIV positioned relative to container (using left/top produced by handler) */}
      {hoveredPoint && (
        <div
          className="tooltip"
          style={{
            position: "absolute",
            left: `calc(${hoveredPoint.left}px - 70px)`,
            top: `${hoveredPoint.top - 20}px`,
            transform: "translateY(-50%)",
            pointerEvents: "none",
            whiteSpace: "nowrap",
            height: "fit-content",
          }}
        >
          <p>
            {hoveredPoint.label}: {hoveredPoint.value.toFixed(2)}
          </p>
        </div>
      )}
    </div>
  );
}
