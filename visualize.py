import plotly.graph_objects as go
import numpy as np

def get_decomposition_animation(decomposition):
    frames = []
    
    for i in range(len(decomposition)):
        facets_subset = decomposition[:i+1]
        # Reshape data for Plotly Mesh3d
        vertices_flat = np.concatenate(facets_subset).reshape(-1, 3)
        unique_vertices, indices = np.unique(vertices_flat, axis=0, return_inverse=True)
        triangle_indices = indices.reshape(-1, 3)
        x_coords = unique_vertices[:, 0]
        y_coords = unique_vertices[:, 1]
        z_coords = unique_vertices[:, 2]
        i_indices = triangle_indices[:, 0]
        j_indices = triangle_indices[:, 1]
        k_indices = triangle_indices[:, 2]
    
        # Create edges for the current frame
        edges_x = []
        edges_y = []
        edges_z = []
        for facet in facets_subset:
            for j in range(3):
                edges_x.extend([facet[j][0], facet[(j+1)%3][0], None])  # Connect vertex j to vertex (j+1)%3
                edges_y.extend([facet[j][1], facet[(j+1)%3][1], None])
                edges_z.extend([facet[j][2], facet[(j+1)%3][2], None])
    
        frame = go.Frame(
            data=[
                go.Mesh3d(
                    x=x_coords,
                    y=y_coords,
                    z=z_coords,
                    i=i_indices,
                    j=j_indices,
                    k=k_indices,
                    color='lightblue',
                    opacity=1.0
                ),
                go.Scatter3d(  # Add the edges as a Scatter3d trace
                    x=edges_x,
                    y=edges_y,
                    z=edges_z,
                    mode='lines',
                    line=dict(color='black', width=2),
                    name="edges",
                    showlegend=False # Hide legend for edges
                )
    
            ],
            name=f'frame{i}'
        )
        frames.append(frame)
    
    # ... (rest of the code to create the initial figure and display the animation)
    
    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=x_coords,
                y=y_coords,
                z=z_coords,
                i=i_indices,
                j=j_indices,
                k=k_indices,
                color='lightblue',
                opacity=1.0
            ),
            go.Scatter3d(  # Add edges for initial state
                x=edges_x,
                y=edges_y,
                z=edges_z,
                mode='lines',
                line=dict(color='black', width=2),
                name="edges",
                showlegend=False
            )
    
        ],
        layout=go.Layout(
            updatemenus=[dict(type="buttons", buttons=[dict(label="Play",
                                                            method="animate",
                                                            args=[None, {"frame": {"duration": 100, "redraw": True},
                                                                        "transition": {"duration": 0}}])])],
            scene=dict(
                aspectmode='data' # Maintain aspect ratio based on data ranges
            ),
        ),
        frames=frames
    )

    return fig