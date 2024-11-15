import os
import sys
import math
import config
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def quit_figure(event):
    if event.key == 'q':
        plt.close(event.canvas.figure)
        sys.exit(0)

class Plotter:
    def __init__(self):
        self.fig, self.ax = plt.subplots()
        # Create a figure and axis object for the plot
        self.liveliness_text = self.ax.text(0.05, 0.95, '', transform=self.ax.transAxes, fontsize=14,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        plt.gcf().canvas.mpl_connect('key_press_event', quit_figure)

    def init(self):
        # Reset plot limits and other properties as needed
        self.ax.set_xlim(-1, 2)
        self.ax.set_ylim(-1, 1)
        self.liveliness_text.set_text(f'Liveliness function = {config.liveliness}')
        return []


    # Function to update the plots
    def plot_live(self, scenario, x_cum, u_cum, metrics):
        self.scenario = scenario
        self.x_cum = np.array(x_cum)
        self.u_cum = np.array(u_cum)
        self.metrics = metrics
        self.update(len(x_cum[0]) - 1)
        plt.legend()
        plt.draw()
        plt.pause(0.05)
        if config.plot_live_pause:
            plt.waitforbuttonpress()


    # Function to update the plots
    def update(self, frame):
        self.ax.clear()

        frame *= config.plot_rate

        # Redraw static elements
        self.scenario.plot(self.ax)

        # Reset plot limits and other properties as needed
        self.ax.set_xlim(min(self.scenario.plot_bounds[:, 0]), max(self.scenario.plot_bounds[:, 0]))
        self.ax.set_ylim(min(self.scenario.plot_bounds[:, 1]), max(self.scenario.plot_bounds[:, 1]))

        u0, u1 = np.round(self.u_cum[0][frame], 2), np.round(self.u_cum[1][frame], 2)
        try:
            L = np.round(self.metrics[frame][0], 2)
            ttc= np.round(self.metrics[frame][1], 2)
            intersects = self.metrics[frame][4]
        except Exception as e:
            print(e)
            L = 0
            ttc = 0
            intersects = False
        x0_state, x1_state = self.x_cum[0][frame].T.copy(), self.x_cum[1][frame].T.copy()
        x0_state[2] = np.rad2deg(x0_state[2])
        x1_state = self.x_cum[1][frame].T.copy()
        x1_state[2] = np.rad2deg(x1_state[2])
        dist = np.linalg.norm(x0_state[:2] - x1_state[:2])
        liveliness_text = [f'Timestamp: {frame * config.sim_ts}',
                           f'Liveliness function = {L}. TTC: {ttc}',
                           f'Agent 0 X = {x0_state}.',
                           f'Agent 0 U = {u0.T}.',
                           f'Agent 1 X = {x1_state}.',
                           f'Agent 1 U = {u1.T}',
                           f'Agent dist: {dist}']

        is_live = False
        if config.consider_intersects:
            if L > config.liveness_threshold or not intersects:
                is_live = True
        else:
            if L > config.liveness_threshold:
                is_live = True
        
        collides = dist < config.agent_radius * 2 + config.safety_dist
        for state in [x0_state, x1_state]:
            for obs in self.scenario.obstacles:
                if np.linalg.norm(state[:2] - np.array(obs[:2])) < config.agent_radius + obs[2] + config.safety_dist:
                    collides = True
        text_color = 'red' if collides else 'green' if is_live else 'magenta'
        self.liveliness_text = self.ax.text(0.05, 0.95, '\n'.join(liveliness_text), transform=self.ax.transAxes, fontsize=10, verticalalignment='top', color=text_color)

        # Determine the start index for the fading effect
        trail_length = 20 * config.plot_rate
        start_index = max(0, frame - trail_length)  # Adjust '10' to control the length of the fading trail

        # Draw the fading trails for agents 1 and 2
        for i in range(start_index, frame - 1, config.plot_rate):
            alpha = 1 - ((frame - 1 - i) / trail_length)**2
            self.ax.plot(self.x_cum[0][i:i+2, 0], self.x_cum[0][i:i+2, 1], 'r-', alpha=alpha, linewidth=5)
            self.ax.plot(self.x_cum[1][i:i+2, 0], self.x_cum[1][i:i+2, 1], 'b-', alpha=alpha, linewidth=5)
        
        if config.plot_arrows:
            pos_diff, vel_diff = self.metrics[frame][2], self.metrics[frame][3]
            self.ax.arrow(0, 0, pos_diff[0], pos_diff[1], head_width=0.05, head_length=0.1, fc='green', ec='green', label='Position difference')
            self.ax.arrow(0, 0, vel_diff[0], vel_diff[1], head_width=0.05, head_length=0.1, fc='orange', ec='orange', label='Velocity difference')
        
        return []


    def plot(self, scenario, x_cum, u_cum, metrics):
        self.scenario = scenario
        self.scenario.plot(self.ax)
        self.x_cum = x_cum
        self.u_cum = u_cum
        self.metrics = metrics

        # Create an animation
        ani = FuncAnimation(self.fig, lambda frame: self.update(frame), frames=len(self.x_cum[0]) // config.plot_rate, init_func=lambda: self.init(), blit=False)

        # Save the animation
        ani.save(os.path.join('animations/', config.ani_save_name), writer='ffmpeg')
        if config.plot_end_ani_only:
            return

        # Set the color palette to "deep"
        sns.set_palette("deep")
        sns.set()
        fontsize = 14

        if config.dynamics == config.DynamicsModel.SINGLE_INTEGRATOR:
            speed1, speed2 = u_cum.copy()
            speed1 = [control[0] for control in speed1]
            speed2 = [control[0] for control in speed2]
        else:
            agent_1_states, agent_2_states = x_cum.copy()
            speed1 = [state[3] for state in agent_1_states]
            speed2 = [state[3] for state in agent_2_states]

        # Creating iteration indices for each agent based on the number of velocity points
        iterations = range(0, len(speed1), config.plot_rate)
        print("Iterations:", list(iterations))

        speed1 = [speed1[idx] for idx in iterations]
        speed2 = [speed2[idx] for idx in iterations]
        liveness = [metrics[idx][0] for idx in iterations]

        # Plotting the velocities as a function of the iteration for both agents
        plt.figure(figsize=(10, 10))

        # Plotting the x and y velocities for Agent 1
        plt.subplot(2, 1, 1)
        sns.lineplot(x=iterations, y=speed1, label='Agent 1 speed', marker='o',markers=True, dashes=False,markeredgewidth=0, linewidth = 5, markersize = 15)
        sns.lineplot(x=iterations, y=speed2, label='Agent 2 speed', marker='o',markers=True, dashes=False,markeredgewidth=0, linewidth = 5, markersize = 15)
        plt.xlabel('Iteration', fontsize = fontsize)
        plt.ylabel('Velocity', fontsize = fontsize)
        plt.legend(loc='upper left', ncol=1, fontsize = fontsize)
        plt.xlim(0, max(iterations))
        plt.xticks(np.arange(0, max(iterations)+1, 4*config.plot_rate), fontsize = fontsize)
        plt.grid(which='major', color='#CCCCCC', linestyle='--')
        plt.grid(which='minor', color='#CCCCCC', linestyle='-', axis='both')
        plt.minorticks_on()

        plt.subplot(2, 1, 2)
        sns.lineplot(x=iterations, y=liveness, label='Liveness value', marker='o', color = 'orange', markers=True, dashes=False,markeredgewidth=0, linewidth = 5, markersize = 15)
        sns.lineplot(x=iterations, y=tuple(np.ones(len(iterations))*.3), label='Threshold', markers=True, dashes=False,markeredgewidth=0, linewidth = 5, markersize = 15)
        #plt.title('Liveness values', fontsize = fontsize)
        plt.xlabel('Iteration', fontsize = fontsize)
        plt.ylabel('Liveness', fontsize = fontsize)
        plt.legend(loc='upper left', ncol=1, fontsize = fontsize)
        plt.xlim(0, max(iterations))
        plt.ylim(0, 1.5)
        plt.xticks(np.arange(0, max(iterations)+1, 4*config.plot_rate), fontsize = fontsize)
        plt.yticks(np.arange(0, 1.6, .2), fontsize = fontsize)
        plt.grid(which='major', color='#CCCCCC', linestyle='--')
        plt.grid(which='minor', color='#CCCCCC', linestyle='-', axis='both')
        plt.minorticks_on()

        plt.tight_layout()
        plt.show()
        plt.show()


