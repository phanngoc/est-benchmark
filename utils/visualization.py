import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any, Optional
import pandas as pd
import networkx as nx
from collections import Counter

class GraphVisualization:
    """Class để tạo visualization cho GraphRAG results"""
    
    @staticmethod
    def create_entity_bar_chart(entities: List[Dict[str, Any]]) -> go.Figure:
        """Tạo bar chart cho entity types"""
        if not entities:
            return go.Figure()
        
        # Count entities by type
        entity_counts = Counter([entity.get('type', 'Unknown') for entity in entities])
        
        fig = go.Figure(data=[
            go.Bar(
                x=list(entity_counts.keys()),
                y=list(entity_counts.values()),
                marker_color=px.colors.qualitative.Set3
            )
        ])
        
        fig.update_layout(
            title="Phân bố Entity Types",
            xaxis_title="Entity Type",
            yaxis_title="Số lượng",
            showlegend=False
        )
        
        return fig
    
    @staticmethod
    def create_network_graph(entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> go.Figure:
        """Tạo network graph cho entities và relationships"""
        if not entities:
            return go.Figure()
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes (entities)
        for entity in entities:
            G.add_node(
                entity.get('name', 'Unknown'),
                type=entity.get('type', 'Unknown'),
                description=entity.get('description', '')
            )
        
        # Add edges (relationships)
        for rel in relationships:
            if 'source' in rel and 'target' in rel:
                G.add_edge(
                    rel['source'],
                    rel['target'],
                    relationship=rel.get('type', 'Unknown')
                )
        
        # Get layout positions
        pos = nx.spring_layout(G, k=1, iterations=50)
        
        # Prepare edge traces
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Prepare node traces
        node_x = []
        node_y = []
        node_text = []
        node_info = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            
            # Get node attributes
            attrs = G.nodes[node]
            info = f"Type: {attrs.get('type', 'Unknown')}<br>"
            if attrs.get('description'):
                info += f"Description: {attrs['description'][:100]}..."
            node_info.append(info)
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="middle center",
            hovertext=node_info,
            marker=dict(
                showscale=True,
                colorscale='YlOrRd',
                reversescale=True,
                color=[],
                size=20,
                colorbar=dict(
                    thickness=15,
                    x=0.9,
                    len=0.5,
                    title="Node Importance"
                ),
                line=dict(width=2)
            )
        )
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title='Knowledge Graph',
                           titlefont_size=16,
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           annotations=[ dict(
                               text="Hover over nodes to see details",
                               showarrow=False,
                               xref="paper", yref="paper",
                               x=0.005, y=-0.002,
                               xanchor='left', yanchor='bottom',
                               font=dict(color="gray", size=12)
                           )],
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                       ))
        
        return fig
    
    @staticmethod
    def create_query_results_table(query_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """Tạo bảng kết quả query"""
        if not query_results:
            return pd.DataFrame()
        
        data = []
        for i, result in enumerate(query_results):
            data.append({
                'STT': i + 1,
                'Query': result.get('query', ''),
                'Response': result.get('response', '')[:200] + '...' if len(result.get('response', '')) > 200 else result.get('response', ''),
                'Timestamp': result.get('timestamp', ''),
                'References': len(result.get('references', []))
            })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def create_references_display(references: List[Dict[str, Any]]) -> str:
        """Tạo HTML để hiển thị references"""
        if not references:
            return "Không có references"
        
        html = "<div style='margin: 10px 0;'>"
        html += "<h4>References:</h4>"
        
        for i, ref in enumerate(references):
            html += f"<div style='margin: 5px 0; padding: 10px; border-left: 3px solid #007bff; background-color: #f8f9fa;'>"
            html += f"<strong>Reference {i+1}:</strong><br>"
            
            if 'source' in ref:
                html += f"<strong>Nguồn:</strong> {ref['source']}<br>"
            if 'content' in ref:
                content = ref['content'][:300] + '...' if len(ref['content']) > 300 else ref['content']
                html += f"<strong>Nội dung:</strong> {content}<br>"
            if 'relevance_score' in ref:
                html += f"<strong>Độ liên quan:</strong> {ref['relevance_score']:.2f}<br>"
            
            html += "</div>"
        
        html += "</div>"
        return html
    
    @staticmethod
    def create_processing_stats(stats: Dict[str, Any]) -> go.Figure:
        """Tạo biểu đồ thống kê xử lý"""
        if not stats:
            return go.Figure()
        
        # Tạo pie chart cho file types
        file_types = stats.get('file_types', {})
        if file_types:
            fig = go.Figure(data=[go.Pie(
                labels=list(file_types.keys()),
                values=list(file_types.values()),
                hole=0.3
            )])
            
            fig.update_layout(
                title="Phân bố loại file đã xử lý",
                showlegend=True
            )
            
            return fig
        
        return go.Figure()
