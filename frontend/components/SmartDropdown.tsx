import React, { useState, useRef, useCallback, useEffect } from 'react';

interface SmartDropdownProps {
  children: React.ReactNode;
  trigger: React.ReactNode;
  placement?: 'auto' | 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  offset?: number;
  className?: string;
}

interface DropdownPosition {
  top?: number;
  bottom?: number;
  left?: number;
  right?: number;
  transform?: string;
}

const SmartDropdown: React.FC<SmartDropdownProps> = ({
  children,
  trigger,
  placement = 'auto',
  offset = 8,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<DropdownPosition>({});
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const calculatePosition = useCallback(() => {
    if (!triggerRef.current || !dropdownRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const dropdownRect = dropdownRef.current.getBoundingClientRect();
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight
    };

    // Calculate available space in all directions
    const spaceRight = viewport.width - triggerRect.right;
    const spaceLeft = triggerRect.left;
    const spaceBottom = viewport.height - triggerRect.bottom;
    const spaceTop = triggerRect.top;

    let newPosition: DropdownPosition = {};

    if (placement === 'auto') {
      // Auto-positioning logic with collision detection
      
      // Horizontal positioning
      if (spaceRight >= dropdownRect.width) {
        // Align right edge of dropdown with right edge of trigger
        newPosition.left = triggerRect.right - dropdownRect.width;
      } else if (spaceLeft >= dropdownRect.width) {
        // Align left edge of dropdown with left edge of trigger
        newPosition.left = triggerRect.left;
      } else {
        // Center if neither side has enough space, but keep within viewport
        const idealLeft = triggerRect.left - (dropdownRect.width - triggerRect.width) / 2;
        newPosition.left = Math.max(8, Math.min(idealLeft, viewport.width - dropdownRect.width - 8));
      }

      // Vertical positioning
      if (spaceBottom >= dropdownRect.height + offset) {
        // Position below trigger
        newPosition.top = triggerRect.bottom + offset;
      } else if (spaceTop >= dropdownRect.height + offset) {
        // Position above trigger
        newPosition.top = triggerRect.top - dropdownRect.height - offset;
      } else {
        // Position wherever there's more space
        if (spaceBottom > spaceTop) {
          newPosition.top = triggerRect.bottom + offset;
        } else {
          newPosition.top = triggerRect.top - dropdownRect.height - offset;
        }
      }
    } else {
      // Manual placement handling
      switch (placement) {
        case 'bottom-right':
          newPosition.left = triggerRect.right - dropdownRect.width;
          newPosition.top = triggerRect.bottom + offset;
          break;
        case 'bottom-left':
          newPosition.left = triggerRect.left;
          newPosition.top = triggerRect.bottom + offset;
          break;
        case 'top-right':
          newPosition.left = triggerRect.right - dropdownRect.width;
          newPosition.top = triggerRect.top - dropdownRect.height - offset;
          break;
        case 'top-left':
          newPosition.left = triggerRect.left;
          newPosition.top = triggerRect.top - dropdownRect.height - offset;
          break;
      }

      // Ensure dropdown stays within viewport bounds
      if (newPosition.left !== undefined) {
        newPosition.left = Math.max(8, Math.min(newPosition.left, viewport.width - dropdownRect.width - 8));
      }
      if (newPosition.top !== undefined) {
        newPosition.top = Math.max(8, Math.min(newPosition.top, viewport.height - dropdownRect.height - 8));
      }
    }

    setPosition(newPosition);
  }, [placement, offset]);

  // Handle escape key press
  useEffect(() => {
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscapeKey);
      return () => {
        document.removeEventListener('keydown', handleEscapeKey);
      };
    }
  }, [isOpen]);

  // Handle position calculation and event listeners
  useEffect(() => {
    if (isOpen) {
      // Initial position calculation
      calculatePosition();
      
      // Add event listeners for dynamic repositioning
      const handleResize = () => calculatePosition();
      const handleScroll = () => calculatePosition();

      window.addEventListener('resize', handleResize);
      window.addEventListener('scroll', handleScroll, true);
      
      return () => {
        window.removeEventListener('resize', handleResize);
        window.removeEventListener('scroll', handleScroll, true);
      };
    }
  }, [isOpen, calculatePosition]);

  const handleTriggerClick = () => {
    setIsOpen(!isOpen);
  };

  const handleBackdropClick = () => {
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        onClick={handleTriggerClick}
        className="focus:outline-none"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {trigger}
      </button>

      {isOpen && (
        <>
          {/* Backdrop for click-outside-to-close functionality */}
          <div
            className="fixed inset-0 z-40"
            onClick={handleBackdropClick}
            aria-hidden="true"
          />
          
          {/* Dropdown menu */}
          <div
            ref={dropdownRef}
            className={`fixed z-50 bg-white rounded-md shadow-lg border border-gray-200 ${className}`}
            style={position}
            role="menu"
            aria-orientation="vertical"
            aria-labelledby="dropdown-button"
          >
            {children}
          </div>
        </>
      )}
    </div>
  );
};

export default SmartDropdown;