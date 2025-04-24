# @title STL Parser

import numpy as np
import struct
import re
from typing import List, Tuple, Optional, cast

class STLParser:
    """
    Parses STL data (ASCII or Binary) from bytes into a NumPy array of facets.

    Attributes:
        normals (np.ndarray): Array of shape (N, 3) containing normal vectors.
        vertices (np.ndarray): Array of shape (N, 3, 3) containing vertices
                                  for N facets. vertices[i] = [[v1x, v1y, v1z],
                                  [v2x, v2y, v2z], [v3x, v3y, v3z]].
    """

    def __init__(self, stl_bytes: bytes):
        """
        Initializes the parser and parses the provided STL bytes.

        Args:
            stl_bytes: The raw byte content of the STL file.

        Raises:
            ValueError: If the data cannot be parsed as either ASCII or Binary STL,
                        or if the file format appears corrupt.
        """
        self._normals_list: List[Tuple[float, float, float]] = []
        self._vertices_list: List[List[Tuple[float, float, float]]] = [] # List of [[v1], [v2], [v3]]

        # Initialize numpy arrays as empty until parsing is successful
        self.normals = np.empty((0, 3), dtype=np.float32)
        self.vertices = np.empty((0, 3, 3), dtype=np.float32)

        self._parse(stl_bytes) # Call the main parsing logic

        # Convert lists to numpy arrays after successful parsing
        if self._vertices_list:
            self.vertices = np.array(self._vertices_list, dtype=np.float32)
        if self._normals_list:
             self.normals = np.array(self._normals_list, dtype=np.float32)


    def _parse(self, stl_bytes: bytes):
        """Determine format and call the appropriate parser."""
        # Basic check: If it starts with 'solid' and isn't suspiciously small, try ASCII
        is_likely_ascii = False
        if stl_bytes[:5].lower() == b'solid' and len(stl_bytes) > 100: # 100 is arbitrary, avoids tiny "solid..." files
             try:
                 # More thorough check: decode a chunk and look for keywords
                 chunk = stl_bytes[:512].decode('ascii', errors='ignore')
                 if 'facet' in chunk or 'vertex' in chunk or 'endsolid' in chunk:
                    is_likely_ascii = True
             except Exception:
                 pass # Decoding failed, likely binary

        parse_error = None
        if is_likely_ascii:
            try:
                self._parse_ascii(stl_bytes)
                if self._vertices_list: # Check if parsing actually found facets
                    return # Successfully parsed as ASCII
            except Exception as ascii_e:
                # Parsing failed, store error and maybe try binary later
                parse_error = ValueError(f"Failed to parse as ASCII STL: {ascii_e}")
                # Clear any partial data before trying binary
                self._normals_list.clear()
                self._vertices_list.clear()
                # Fall through to try binary only if ASCII parsing failed badly


        # If not likely ASCII or ASCII parsing failed, try Binary
        if not self._vertices_list: # Only try binary if ASCII didn't succeed
            try:
                self._parse_binary(stl_bytes)
                if self._vertices_list:
                    return # Successfully parsed as Binary
            except Exception as binary_e:
                 # If ASCII also failed, chain the errors
                 if parse_error:
                     raise ValueError(f"Failed as ASCII ({parse_error}), and failed as Binary ({binary_e})") from binary_e
                 else:
                     raise ValueError(f"Failed to parse as Binary STL: {binary_e}") from binary_e

        # If we reach here and haven't parsed anything successfully
        if not self._vertices_list:
            if parse_error: # If ASCII parsing failed earlier
                 raise parse_error
            else: # If neither seemed to work
                 raise ValueError("Could not parse STL data. Unknown format or invalid/empty file.")


    def _parse_ascii(self, stl_bytes: bytes):
        """Parses ASCII STL data."""
        try:
            # Use 'latin-1' or 'utf-8' with error handling for robustness
            stl_text = stl_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            raise ValueError("Failed to decode ASCII STL bytes.") from e

        # Slightly more forgiving regex, handles potential extra whitespace & case
        facet_pattern = re.compile(
            r"facet\s+normal\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)"
            r"\s*outer\s+loop"
            r"\s*vertex\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)"
            r"\s*vertex\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)"
            r"\s*vertex\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)\s+([\d\.\-eE+]+)"
            r"\s*endloop"
            r"\s*endfacet", re.IGNORECASE | re.MULTILINE)

        temp_normals = []
        temp_vertices = []
        for match in facet_pattern.finditer(stl_text):
            try:
                n = tuple(map(float, match.groups()[0:3]))
                v1 = tuple(map(float, match.groups()[3:6]))
                v2 = tuple(map(float, match.groups()[6:9]))
                v3 = tuple(map(float, match.groups()[9:12]))
                temp_normals.append(n)
                # Store vertices as list of lists for direct numpy conversion later
                temp_vertices.append([list(v1), list(v2), list(v3)])
            except (ValueError, IndexError) as e:
                 # Allows skipping over potentially malformed facets in ASCII
                 print(f"Warning: Skipping malformed ASCII facet: {e}")
                 continue

        if not temp_vertices:
            # If regex found nothing, maybe it's not really ASCII
            raise ValueError("No valid facets found in ASCII STL data.")

        self._normals_list = temp_normals
        self._vertices_list = temp_vertices


    def _parse_binary(self, stl_bytes: bytes):
        """Parses Binary STL data."""
        if len(stl_bytes) < 84:
            raise ValueError(f"Binary STL file too small ({len(stl_bytes)} bytes). Needs at least 84 bytes.")

        # Header (80 bytes, unused)
        # struct.unpack returns a tuple, need [0]
        try:
            num_triangles = struct.unpack('<I', stl_bytes[80:84])[0]
        except struct.error as e:
            raise ValueError("Could not read triangle count from binary STL header.") from e

        expected_size = 84 + num_triangles * 50
        # Allow slightly different sizes? No, binary should be exact.
        if len(stl_bytes) != expected_size:
            # If size mismatch AND it started with b'solid', it was probably misidentified ASCII
            if stl_bytes.strip().startswith(b'solid'):
                 raise ValueError(f"File starts with 'solid' but size {len(stl_bytes)} doesn't match binary expectation {expected_size} for {num_triangles} triangles. Likely misidentified ASCII.")
            else:
                 raise ValueError(f"Binary STL file size mismatch. Header indicates {num_triangles} triangles (expected size {expected_size}), but file size is {len(stl_bytes)}.")

        if num_triangles == 0:
            # Valid empty binary STL
             self._normals_list = []
             self._vertices_list = []
             return

        temp_normals = []
        temp_vertices = []
        offset = 84
        # '<12fH': little-endian, 12 floats (normal*3, v1*3, v2*3, v3*3), 1 unsigned short (attribute byte count)
        triangle_struct = struct.Struct('<12fH')

        for i in range(num_triangles):
            try:
                # Unpack data for one triangle
                data = triangle_struct.unpack(stl_bytes[offset:offset + 50])

                n = tuple(data[0:3])
                v1 = tuple(data[3:6])
                v2 = tuple(data[6:9])
                v3 = tuple(data[9:12])
                # attr_bytes = data[12] # We ignore attribute byte count

                temp_normals.append(n)
                temp_vertices.append([list(v1), list(v2), list(v3)])

                offset += 50
            except struct.error as e:
                raise ValueError(f"Failed to unpack binary triangle data at index {i} (offset {offset}). File likely corrupt.") from e
            except IndexError as e:
                 raise ValueError(f"File ended prematurely while reading triangle {i}. Expected {num_triangles} triangles.") from e

        self._normals_list = temp_normals
        self._vertices_list = temp_vertices

    def get_facets_numpy(self) -> np.ndarray:
        """
        Returns the facets (triangles) of the STL model as a NumPy array.

        The vertices for each facet are ordered consistently as they appeared
        in the file (v1, v2, v3).

        Returns:
            np.ndarray: An array of shape (N, 3, 3), where N is the number
                        of facets. Each facet is represented by its 3 vertices,
                        and each vertex has 3 coordinates (x, y, z).
                        Data type is float32. Returns an empty array (0, 3, 3)
                        if parsing failed or the file was empty.
        """
        # The conversion to numpy happens in __init__ after successful parse
        return self.vertices

    def get_normals_numpy(self) -> np.ndarray:
        """
        Returns the normal vectors read from the STL file as a NumPy array.

        Note: These are the normals *as stored in the file*. They might not be
        unit vectors or accurately calculated.

        Returns:
            np.ndarray: An array of shape (N, 3), where N is the number
                        of facets. Each row is the normal vector (nx, ny, nz)
                        for the corresponding facet in get_facets_numpy().
                        Data type is float32. Returns an empty array (0, 3)
                        if parsing failed or the file was empty.
        """
         # The conversion to numpy happens in __init__ after successful parse
        return self.normals
