"""Third-person camera — orbit behind the player with a natural viewing angle."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Camera sits behind-right and above the player (not glued to their back).
CAM_DISTANCE = 5.0
CAM_HEIGHT = 2.4
CAM_SIDE_OFFSET = 0.85
CAM_LOOK_HEIGHT = 1.15  # look-at point on player (chest)
MIN_PITCH = -0.55
MAX_PITCH = 0.25


def third_person_camera_eye(
    px: float,
    py: float,
    pz: float,
    yaw: float,
    pitch: float,
) -> tuple[float, float, float]:
    """World-space camera position for gluLookAt."""
    pitch = max(MIN_PITCH, min(MAX_PITCH, pitch))
    dist = CAM_DISTANCE * math.cos(pitch)
    lift = CAM_HEIGHT + CAM_DISTANCE * math.sin(-pitch)

    back_x = -math.sin(yaw) * dist
    back_z = math.cos(yaw) * dist
    side_x = math.cos(yaw) * CAM_SIDE_OFFSET
    side_z = math.sin(yaw) * CAM_SIDE_OFFSET

    return px + back_x + side_x, py + lift, pz + back_z + side_z


def third_person_look_at(py: float) -> float:
    return py + CAM_LOOK_HEIGHT


def apply_twin_camera(
    px: float,
    py: float,
    pz: float,
    yaw: float,
    *,
    height: float = 80.0,
    distance: float = 55.0,
) -> None:
    """Elevated fly camera for digital twin mode."""
    from OpenGL.GLU import gluLookAt

    back_x = -math.sin(yaw) * distance
    back_z = math.cos(yaw) * distance
    ex = px + back_x
    ez = pz + back_z
    ey = py + height
    gluLookAt(ex, ey, ez, px, py, pz, 0.0, 1.0, 0.0)


def apply_third_person_camera(
    px: float,
    py: float,
    pz: float,
    yaw: float,
    pitch: float,
) -> None:
    """Position the OpenGL camera in third-person view."""
    from OpenGL.GLU import gluLookAt

    ex, ey, ez = third_person_camera_eye(px, py, pz, yaw, pitch)
    ly = third_person_look_at(py)
    gluLookAt(ex, ey, ez, px, ly, pz, 0.0, 1.0, 0.0)


@dataclass
class FreeFlyCamera:
    """Detached camera for photo mode — WASD + mouse look, no collision."""

    x: float = 0.0
    y: float = 8.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = -0.25
    speed: float = 18.0
    fov: float = 70.0

    def move(self, forward: float, strafe: float, vertical: float, dt: float) -> None:
        import math

        pitch = max(MIN_PITCH, min(MAX_PITCH, self.pitch))
        self.pitch = pitch
        fx = -math.sin(self.yaw)
        fz = math.cos(self.yaw)
        rx = math.cos(self.yaw)
        rz = math.sin(self.yaw)
        step = self.speed * dt
        self.x += (fx * forward + rx * strafe) * step
        self.z += (fz * forward + rz * strafe) * step
        self.y += vertical * step

    def apply(self) -> None:
        import math
        from OpenGL.GLU import gluLookAt

        pitch = max(MIN_PITCH, min(MAX_PITCH, self.pitch))
        fx = -math.sin(self.yaw) * math.cos(pitch)
        fy = math.sin(-pitch)
        fz = math.cos(self.yaw) * math.cos(pitch)
        tx = self.x + fx
        ty = self.y + fy
        tz = self.z + fz
        gluLookAt(self.x, self.y, self.z, tx, ty, tz, 0.0, 1.0, 0.0)
