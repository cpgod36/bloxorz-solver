"""Simple clickable 3D-styled button widget for Pygame."""

from __future__ import annotations

from collections.abc import Callable
import pygame


class Button:
    """Rectangular button with 3D depth, hover lift, and click callback."""

    def __init__(
        self,
        rect: tuple[int, int, int, int],
        label: str,
        on_click: Callable[[], None],
        enabled: bool = True,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.enabled = enabled

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process mouse click event; return True if clicked."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Render the button with a 3D bottom shadow and hover animation."""
        mouse_pos = pygame.mouse.get_pos()
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pressed = hovered and pygame.mouse.get_pressed()[0]

        if not self.enabled:
            bg = (50, 56, 68)
            fg = (115, 122, 135)
            border = (70, 78, 92)
            offset_y = 0
        elif pressed:
            bg = (64, 128, 215)
            fg = (255, 255, 255)
            border = (140, 195, 255)
            offset_y = 2
        elif hovered:
            bg = (82, 152, 245)
            fg = (255, 255, 255)
            border = (155, 208, 255)
            offset_y = -1
        else:
            bg = (58, 68, 88)
            fg = (235, 240, 245)
            border = (95, 110, 135)
            offset_y = 0

        # 3D base shadow
        shadow_rect = self.rect.move(0, 3)
        pygame.draw.rect(surface, (18, 22, 30), shadow_rect, border_radius=6)

        draw_rect = self.rect.move(0, offset_y)
        pygame.draw.rect(surface, bg, draw_rect, border_radius=6)
        pygame.draw.rect(surface, border, draw_rect, width=1, border_radius=6)

        if self.enabled:
            shadow_surf = font.render(self.label, True, (18, 22, 32))
            shadow_rect_txt = shadow_surf.get_rect(center=(draw_rect.centerx, draw_rect.centery + 1))
            surface.blit(shadow_surf, shadow_rect_txt)

        text_surf = font.render(self.label, True, fg)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        surface.blit(text_surf, text_rect)
