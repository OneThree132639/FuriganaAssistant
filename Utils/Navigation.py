import logging

from PyQt5.QtWidgets import QLayout
from typing import Dict, List, Optional, Protocol, runtime_checkable, Tuple

@runtime_checkable
class NavigableWidget(Protocol): 
	row: int
	col: int
	def setFocus(self) -> None: ...
	def setCursorToEdge(self, dx: int) -> None: ...
	def isVisible(self) -> bool: ...
	def isEnabled(self) -> bool: ...

class BoundaryPolicy: 
	def resolve(self, current: Tuple[int, int], 
			target: Tuple[int, int], all_positions: List[Tuple[int, int]]
		) -> Optional[Tuple[int, int]]: 
		raise NotImplementedError
	
class BlockBoundaryPolicy(BoundaryPolicy): 
	def resolve(self, current: Tuple[int, int], 
			target: Tuple[int, int], all_positions: List[Tuple[int, int]]
		) -> Optional[Tuple[int, int]]: 
		if target in all_positions: 
			return target
		else: 
			logging.warning((
				"[BlockBoundaryPolicy.resolve] "
				"Target position {} is out of bounds. Navigation blocked. \n"
				"Current position: {}. \n"
				"All positions: {}. "
			).format(target, current, all_positions))
			return None
	
class WrapBoundaryPolicy(BoundaryPolicy): 
	def resolve(self, current: Tuple[int, int], 
			target: Tuple[int, int], all_positions: List[Tuple[int, int]]
		) -> Optional[Tuple[int, int]]: 
		if target not in all_positions: 
			same_row = [pos for pos in all_positions if pos[0] == target[0]]
			same_col = [pos for pos in all_positions if pos[1] == target[1]]
			dx = target[1] - current[1]
			dy = target[0] - current[0]
			if dx != 0: 
				return min(same_row, key=lambda p: p[1]) if dx > 0 else max(same_row, key=lambda p: p[1])
			else: 
				return min(same_col, key=lambda p: p[0]) if dy > 0 else max(same_col, key=lambda p: p[0])
		return target
	
class FilterPolicy: 
	def should_navigate_to(self, widget: NavigableWidget) -> bool: 
		return widget.isVisible() and widget.isEnabled()
	
class NavigationManager: 

	def __init__(self, boundary_policy: Optional[BoundaryPolicy] = None, 
			filter_policy: Optional[FilterPolicy] = None
		): 
		self._position_map: Dict[Tuple[int, int], NavigableWidget] = {}
		self._boundary_policy = boundary_policy if boundary_policy is not None else BlockBoundaryPolicy()
		self._filter_policy = filter_policy if filter_policy is not None else FilterPolicy()

	def register(self, widget: NavigableWidget) -> None: 
		self._position_map[(widget.row, widget.col)] = widget

	def unregister(self, widget: NavigableWidget) -> None: 
		pos = (widget.row, widget.col)
		if pos in self._position_map and self._position_map[pos] is widget: 
			self._position_map.pop(pos)

	def navigate(self, from_widget: NavigableWidget, dx: int, dy: int) -> bool: 
		current_pos = (from_widget.row, from_widget.col)
		target_pos = (current_pos[0] + dy, current_pos[1] + dx)

		resolved_pos = self._boundary_policy.resolve(
			current_pos, target_pos, list(self._position_map.keys())
		)
		if resolved_pos is None: 
			logging.warning((
				"[NavigationManager.navigate] "
				"No resolution found for navigation from {} to {}. Navigation ignored. "
			).format(current_pos, target_pos))
			return False
		
		target_widget = self._position_map.get(resolved_pos, None)
		if target_widget is None or not self._filter_policy.should_navigate_to(target_widget): 
			logging.warning((
				"[NavigationManager.navigate] "
				"Target widget at position {} is not navigable. Navigation ignored. "
			).format(resolved_pos))
			return False
		
		target_widget.setFocus()
		target_widget.setCursorToEdge(dx)
		return True
	
	def rebuild_from_layout(self, layout: QLayout) -> None: 
		self._position_map.clear()
		for i in range(layout.count()): 
			item = layout.itemAt(i)
			if item is None: 
				continue
			widget = item.widget()
			if isinstance(widget, NavigableWidget): 
				self.register(widget)