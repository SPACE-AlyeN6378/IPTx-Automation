import networkx as nx
import matplotlib.pyplot as plt

# Create a sample network graph
G = nx.Graph()
G.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 1)])

# Specify the edge colors using a color map
edge_colors = ['blue', 'green', 'red', 'purple']

# Draw the network graph with specified edge colors
pos = nx.spring_layout(G)
nx.draw_spring(G, with_labels=True, node_size=700, node_color='lightblue', font_size=10, font_color='darkblue', font_weight='bold', edge_color=edge_colors, width=2.0)

# Show the plot
plt.show()

